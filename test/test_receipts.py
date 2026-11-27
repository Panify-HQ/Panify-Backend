from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.orders import confirm_order
from app.api.v1.receipts import download_receipt_pdf
from app.api.v1.router import api_router
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db
from app.models.cliente import Cliente
from app.models.detalle_pedido import DetallePedido
from app.models.domiciliario import Domiciliario
from app.models.pedidos import Pedido
from app.models.productos import Productos
from app.models.recibos import Recibos
from app.models.roles import Rol
from app.models.usuario import Usuario
from app.schemas.receipt import ReceiptOrderDetail
from app.schemas.user import UserRole
from app.services.receipt_service import (
    ReceiptConflictError,
    ReceiptForbiddenError,
    ReceiptService,
)


def test_receipt_detail_normalizes_mysql_zero_delivery_date():
    order = ReceiptOrderDetail.model_validate(
        {
            "idPedido": 1,
            "estadoPedido": "En preparación",
            "fechaHoraCreacion": datetime(2026, 11, 24, 10, 0),
            "fechaHoraEntregaEstimada": "0000-00-00 00:00:00",
        }
    )

    assert order.fechaHoraEntregaEstimada is None


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def add_customer(db: Session, customer_id: int, user_id: int) -> Usuario:
    role = db.get(Rol, 5)
    if role is None:
        role = Rol(idRol=5, nombre=UserRole.CLIENTE.value)
        db.add(role)
    customer = Cliente(
        idCliente=customer_id,
        tipoCliente="Nuevo",
        direccion=f"Dirección {customer_id}",
    )
    user = Usuario(
        idUsuario=user_id,
        nombre=f"Cliente{user_id}",
        apellido="Prueba",
        correo=f"cliente{user_id}@example.com",
        contrasena="hash",
        telefono="3001234567",
        estado="Activo",
        Rol_idRol=5,
        cliente_idCliente=customer_id,
    )
    db.add_all([customer, user])
    db.flush()
    return user


def add_order(
    db: Session,
    order_id: int,
    customer_id: int,
    *,
    state: str = "Pendiente",
    quantity: int = 2,
    price: Decimal = Decimal("1250.50"),
) -> Pedido:
    order = Pedido(
        idPedido=order_id,
        fechaHoraCreacion=datetime(2026, 11, 24, 10, 0),
        fechaHoraEntregaEstimada=datetime(2026, 11, 24, 12, 0),
        estadoPedido=state,
        cliente_idCliente=customer_id,
    )
    product = Productos(
        idProducto=order_id,
        nombre=f"Pan {order_id}",
        precio=9999.0,
        estado="ACTIVO",
        descripcion="Producto de prueba",
    )
    line = DetallePedido(
        precioFijo=price,
        cantidad=quantity,
        pedido_idPedido=order_id,
        producto_idProducto=order_id,
    )
    db.add_all([order, product, line])
    db.flush()
    return order


def test_confirm_emits_one_receipt_from_frozen_prices(db):
    add_customer(db, customer_id=10, user_id=20)
    add_order(db, order_id=30, customer_id=10)

    receipt = ReceiptService.confirm_order(db, 30)

    assert receipt.totalPagar == Decimal("2501.00")
    assert receipt.fechaEmision is not None
    assert db.get(Pedido, 30).estadoPedido == "En preparación"
    assert len(db.scalars(select(Recibos)).all()) == 1
    with pytest.raises(ReceiptConflictError):
        ReceiptService.confirm_order(db, 30)
    assert len(db.scalars(select(Recibos)).all()) == 1


@pytest.mark.parametrize(
    ("account_state", "line_count"),
    [("Inactivo", 1), ("Activo", 0)],
)
def test_invalid_order_is_not_confirmed_or_billed(db, account_state, line_count):
    customer = add_customer(db, customer_id=11, user_id=21)
    customer.estado = account_state
    order = add_order(db, order_id=31, customer_id=11)
    if line_count == 0:
        db.query(DetallePedido).filter_by(pedido_idPedido=31).delete()
    db.commit()

    with pytest.raises(ReceiptConflictError):
        ReceiptService.confirm_order(db, 31)

    assert db.get(Pedido, 31).estadoPedido == "Pendiente"
    assert db.scalar(select(Recibos).where(Recibos.pedido_idPedido == 31)) is None


def test_receipt_search_pagination_and_customer_ownership(db):
    owner = add_customer(db, customer_id=12, user_id=22)
    other_customer = add_customer(db, customer_id=13, user_id=23)
    add_order(db, order_id=32, customer_id=12)
    add_order(db, order_id=33, customer_id=12)
    add_order(db, order_id=34, customer_id=13)
    db.commit()
    ReceiptService.confirm_order(db, 32)
    ReceiptService.confirm_order(db, 33)
    ReceiptService.confirm_order(db, 34)

    page = ReceiptService.list_receipts(
        db, current_user=owner, search="33", page=1, page_size=1
    )
    assert page["total"] == 1
    assert page["items"][0]["pedido"]["idPedido"] == 33

    first_page = ReceiptService.list_receipts(
        db, current_user=owner, search=None, page=1, page_size=1
    )
    second_page = ReceiptService.list_receipts(
        db, current_user=owner, search=None, page=2, page_size=1
    )
    assert first_page["total"] == 2
    assert second_page["total"] == 2
    assert first_page["items"][0]["idRecibo"] != second_page["items"][0]["idRecibo"]

    receipt = db.scalar(select(Recibos).where(Recibos.pedido_idPedido == 34))
    with pytest.raises(ReceiptForbiddenError):
        ReceiptService.get_receipt_detail(db, receipt.idRecibo, owner)

    other_user = db.get(Usuario, 23)
    detail = ReceiptService.get_receipt_detail(db, receipt.idRecibo, other_user)
    assert detail["productos"][0]["precioUnitario"] == Decimal("1250.50")
    assert detail["productos"][0]["subtotal"] == Decimal("2501.00")


def test_staff_receipt_visibility_follows_role_and_assignment(db):
    add_customer(db, customer_id=15, user_id=25)
    delivery = Domiciliario(idDomiciliario=70, estadoDisponibilidad="Libre")
    admin_role = Rol(idRol=2, nombre=UserRole.ADMINISTRADOR.value)
    baker_role = Rol(idRol=3, nombre=UserRole.PANADERO.value)
    delivery_role = Rol(idRol=4, nombre=UserRole.DOMICILIARIO.value)
    admin = Usuario(
        idUsuario=26,
        nombre="Admin",
        apellido="Prueba",
        correo="admin@example.com",
        contrasena="hash",
        telefono="3001234568",
        estado="Activo",
        Rol_idRol=2,
    )
    baker = Usuario(
        idUsuario=27,
        nombre="Panadero",
        apellido="Prueba",
        correo="panadero@example.com",
        contrasena="hash",
        telefono="3001234569",
        estado="Activo",
        Rol_idRol=3,
    )
    courier = Usuario(
        idUsuario=28,
        nombre="Domiciliario",
        apellido="Prueba",
        correo="domiciliario@example.com",
        contrasena="hash",
        telefono="3001234570",
        estado="Activo",
        Rol_idRol=4,
        domiciliario_idDomiciliario=70,
    )
    db.add_all([delivery, admin_role, baker_role, delivery_role, admin, baker, courier])
    order = add_order(db, order_id=36, customer_id=15)
    order.domiciliario_idDomiciliario = 70
    db.commit()
    receipt = ReceiptService.confirm_order(db, 36)

    assert (
        ReceiptService.list_receipts(
            db, current_user=admin, search=None, page=1, page_size=20
        )["total"]
        == 1
    )
    assert (
        ReceiptService.list_receipts(
            db, current_user=courier, search=None, page=1, page_size=20
        )["total"]
        == 1
    )
    assert (
        ReceiptService.get_receipt_detail(db, receipt.idRecibo, courier)["idRecibo"]
        == receipt.idRecibo
    )
    with pytest.raises(ReceiptForbiddenError):
        ReceiptService.list_receipts(
            db, current_user=baker, search=None, page=1, page_size=20
        )


def test_confirmation_endpoint_authorizes_bakers_only_for_generation(db):
    add_customer(db, customer_id=16, user_id=29)
    baker_role = Rol(idRol=3, nombre=UserRole.PANADERO.value)
    baker = Usuario(
        idUsuario=30,
        nombre="Panadero",
        apellido="Prueba",
        correo="confirmador@example.com",
        contrasena="hash",
        telefono="3001234571",
        estado="Activo",
        Rol_idRol=3,
    )
    db.add_all([baker_role, baker])
    add_order(db, order_id=37, customer_id=16)
    db.commit()

    response = confirm_order(37, db, baker)
    assert response == {
        "idPedido": 37,
        "estadoPedido": "En preparación",
        "reciboGenerado": True,
    }

    customer = db.get(Usuario, 29)
    with pytest.raises(HTTPException) as error:
        confirm_order(38, db, customer)
    assert error.value.status_code == 403


def test_receipt_list_rejects_invalid_pagination_and_long_search(db):
    owner = add_customer(db, customer_id=17, user_id=31)
    test_app = FastAPI()
    test_app.include_router(api_router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = lambda: db
    test_app.dependency_overrides[get_current_user] = lambda: owner

    with TestClient(test_app) as client:
        invalid_page = client.get("/api/v1/receipts", params={"page": 0})
        long_search = client.get(
            "/api/v1/receipts",
            params={"search": "x" * 101},
        )

    assert invalid_page.status_code == 422
    assert long_search.status_code == 422


def test_pdf_download_returns_a_pdf_attachment(db):
    owner = add_customer(db, customer_id=14, user_id=24)
    add_order(db, order_id=35, customer_id=14)
    db.commit()
    receipt = ReceiptService.confirm_order(db, 35)

    response = download_receipt_pdf(receipt.idRecibo, db, owner)

    assert response.media_type == "application/pdf"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="recibo-{receipt.idRecibo}.pdf"'
    )
    assert response.body.startswith(b"%PDF")
