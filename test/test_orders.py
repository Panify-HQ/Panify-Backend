from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.v1.router import api_router
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db
from app.models.cliente import Cliente
from app.models.detalle_pedido import DetallePedido
from app.models.domiciliario import Domiciliario
from app.models.inventarios import Inventarios
from app.models.pedidos import Pedido
from app.models.productos import Productos
from app.models.roles import Rol
from app.models.usuario import Usuario
from app.schemas.order import (
    OrderCreate,
    OrderProductCreate,
    OrderState,
    OrderStatusUpdate,
)
from app.schemas.user import UserRole
from app.services.order_service import (
    OrderConflictError,
    OrderForbiddenError,
    OrderInvalidError,
    OrderService,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def add_user(
    db: Session,
    *,
    user_id: int,
    role_id: int,
    role_name: str,
    customer_id: int | None = None,
    courier_id: int | None = None,
) -> Usuario:
    if db.get(Rol, role_id) is None:
        db.add(Rol(idRol=role_id, nombre=role_name))
    if customer_id is not None and db.get(Cliente, customer_id) is None:
        db.add(
            Cliente(
                idCliente=customer_id,
                tipoCliente="Nuevo",
                direccion=f"Calle {customer_id}",
            )
        )
    if courier_id is not None and db.get(Domiciliario, courier_id) is None:
        db.add(
            Domiciliario(
                idDomiciliario=courier_id,
                estadoDisponibilidad="Libre",
            )
        )
    user = Usuario(
        idUsuario=user_id,
        nombre=f"Usuario{user_id}",
        apellido="Prueba",
        correo=f"usuario{user_id}@example.com",
        contrasena="hash",
        telefono="3001234567",
        estado="Activo",
        Rol_idRol=role_id,
        cliente_idCliente=customer_id,
        domiciliario_idDomiciliario=courier_id,
    )
    db.add(user)
    db.flush()
    return user


def add_product(
    db: Session,
    *,
    product_id: int = 1,
    price: float = 1250.5,
    stocks: tuple[int, ...] = (5,),
) -> Productos:
    product = Productos(
        idProducto=product_id,
        nombre=f"Pan {product_id}",
        precio=price,
        estado="ACTIVO",
        descripcion="Producto de prueba",
    )
    db.add(product)
    db.flush()
    db.add_all(
        [
            Inventarios(
                stockMinimo=1,
                stockActual=stock,
                producto_idProducto=product_id,
            )
            for stock in stocks
        ]
    )
    db.flush()
    return product


def add_order(
    db: Session,
    *,
    order_id: int,
    customer_id: int,
    product_id: int,
    state: str = OrderState.PENDIENTE.value,
    created_at: datetime | None = None,
    quantity: int = 2,
    price: Decimal = Decimal("1250.50"),
) -> Pedido:
    order = Pedido(
        idPedido=order_id,
        fechaHoraCreacion=created_at or datetime(2026, 11, 24, 10, 0),
        fechaHoraEntregaEstimada=datetime(2026, 11, 25, 12, 0),
        estadoPedido=state,
        cliente_idCliente=customer_id,
    )
    db.add(order)
    db.add(
        DetallePedido(
            precioFijo=price,
            cantidad=quantity,
            pedido_idPedido=order_id,
            producto_idProducto=product_id,
        )
    )
    db.flush()
    return order


def test_admin_can_create_order_for_customer(db, monkeypatch):
    now = datetime(2026, 11, 24, 10, 0)
    admin = add_user(
        db,
        user_id=22,
        role_id=1,
        role_name=UserRole.ADMINISTRADOR.value,
    )
    add_user(
        db,
        user_id=23,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=10,
    )
    add_product(db, stocks=(5,))
    db.commit()
    monkeypatch.setattr(OrderService, "_now", staticmethod(lambda: now))
    data = OrderCreate(
        cliente_idCliente=10,
        listaProductos=[OrderProductCreate(idProducto=1, cantidad=2)],
        fechaHoraEntregaEstimada=now + timedelta(hours=2),
    )

    response = OrderService.create_order(db, data, admin)

    assert response["estadoPedido"] == OrderState.PENDIENTE.value
    saved_order = db.get(Pedido, response["idPedido"])
    assert saved_order.cliente_idCliente == 10


def test_create_order_freezes_price_and_consumes_combined_inventory(db, monkeypatch):
    now = datetime(2026, 11, 24, 10, 0)
    customer = add_user(
        db,
        user_id=20,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=10,
    )
    product = add_product(db, stocks=(1, 4))
    monkeypatch.setattr(OrderService, "_now", staticmethod(lambda: now))
    data = OrderCreate(
        listaProductos=[OrderProductCreate(idProducto=1, cantidad=3)],
        fechaHoraEntregaEstimada=now + timedelta(hours=2),
    )

    response = OrderService.create_order(db, data, customer)

    assert response["estadoPedido"] == OrderState.PENDIENTE.value
    assert response["detalles_pedido"][0]["precioFijo"] == Decimal("1250.50")
    assert response["total"] == Decimal("3751.50")
    stock = db.scalars(
        select(Inventarios)
        .where(Inventarios.producto_idProducto == 1)
        .order_by(Inventarios.idInventario)
    ).all()
    assert [row.stockActual for row in stock] == [0, 2]

    product.precio = 9999
    db.commit()
    saved_order = db.get(Pedido, response["idPedido"])
    assert saved_order.cliente_idCliente == 10
    assert OrderService._total(saved_order) == Decimal("3751.50")


def test_customer_cannot_create_order_for_another_customer(db, monkeypatch):
    now = datetime(2026, 11, 24, 10, 0)
    customer = add_user(
        db,
        user_id=40,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=23,
    )
    add_product(db)
    monkeypatch.setattr(OrderService, "_now", staticmethod(lambda: now))
    data = OrderCreate(
        cliente_idCliente=24,
        listaProductos=[OrderProductCreate(idProducto=1, cantidad=1)],
        fechaHoraEntregaEstimada=now + timedelta(hours=2),
    )

    with pytest.raises(OrderForbiddenError):
        OrderService.create_order(db, data, customer)


def test_create_order_rolls_back_when_stock_is_insufficient(db, monkeypatch):
    now = datetime(2026, 11, 24, 10, 0)
    customer = add_user(
        db,
        user_id=21,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=11,
    )
    add_product(db, stocks=(1, 1))
    db.commit()
    monkeypatch.setattr(OrderService, "_now", staticmethod(lambda: now))
    data = OrderCreate(
        cliente_idCliente=11,
        listaProductos=[OrderProductCreate(idProducto=1, cantidad=3)],
        fechaHoraEntregaEstimada=now + timedelta(hours=2),
    )

    with pytest.raises(OrderConflictError, match="disponibles 2"):
        OrderService.create_order(db, data, customer)

    assert db.scalars(select(Pedido)).all() == []
    assert db.scalars(select(DetallePedido)).all() == []
    assert sum(db.scalars(select(Inventarios.stockActual)).all()) == 2


def test_same_day_delivery_after_cutoff_is_rejected(db, monkeypatch):
    now = datetime(2026, 11, 24, 10, 0)
    customer = add_user(
        db,
        user_id=22,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=12,
    )
    add_product(db)
    monkeypatch.setattr(OrderService, "_now", staticmethod(lambda: now))
    data = OrderCreate(
        cliente_idCliente=12,
        listaProductos=[OrderProductCreate(idProducto=1, cantidad=1)],
        fechaHoraEntregaEstimada=datetime(2026, 11, 24, 18, 1),
    )

    with pytest.raises(OrderInvalidError, match="desde el día siguiente"):
        OrderService.create_order(db, data, customer)

    assert db.scalars(select(Pedido)).all() == []


def test_customer_cancellation_restores_stock_only_once(db):
    customer = add_user(
        db,
        user_id=23,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=13,
    )
    add_product(db, stocks=(2, 2))
    order = add_order(
        db,
        order_id=30,
        customer_id=13,
        product_id=1,
        quantity=3,
    )
    db.commit()

    response = OrderService.cancel_order(db, order.idPedido, customer)

    assert response["estadoPedido"] == OrderState.CANCELADO.value
    assert sum(db.scalars(select(Inventarios.stockActual)).all()) == 7
    with pytest.raises(OrderConflictError):
        OrderService.cancel_order(db, order.idPedido, customer)
    assert sum(db.scalars(select(Inventarios.stockActual)).all()) == 7


def test_administrator_can_cancel_active_order_and_restore_inventory(db):
    administrator = add_user(
        db,
        user_id=33,
        role_id=2,
        role_name=UserRole.ADMINISTRADOR.value,
    )
    add_user(
        db,
        user_id=34,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=18,
    )
    add_user(
        db,
        user_id=35,
        role_id=4,
        role_name=UserRole.DOMICILIARIO.value,
        courier_id=71,
    )
    add_product(db, stocks=(0, 0))
    order = add_order(
        db,
        order_id=33,
        customer_id=18,
        product_id=1,
        state=OrderState.EN_CAMINO.value,
        quantity=2,
    )
    order.domiciliario_idDomiciliario = 71
    db.commit()

    response = OrderService.cancel_order(db, order.idPedido, administrator)

    assert response["estadoPedido"] == OrderState.CANCELADO.value
    assert sum(db.scalars(select(Inventarios.stockActual)).all()) == 2


def test_order_listing_applies_customer_scope_and_product_name_filter(db):
    customer = add_user(
        db,
        user_id=36,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=19,
    )
    add_user(
        db,
        user_id=37,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=20,
    )
    add_product(db, product_id=1, stocks=(2,))
    add_product(db, product_id=2, stocks=(2,))
    add_order(
        db,
        order_id=34,
        customer_id=19,
        product_id=1,
        created_at=datetime(2026, 11, 24, 9, 0),
    )
    add_order(
        db,
        order_id=35,
        customer_id=20,
        product_id=2,
        created_at=datetime(2026, 11, 24, 10, 0),
    )
    db.commit()

    response = OrderService.list_orders(
        db,
        customer,
        estado=None,
        text_filter="Pan 1",
        page=1,
        page_size=20,
    )

    assert response["total"] == 1
    assert response["items"][0]["idPedido"] == 34
    assert response["items"][0]["grupoEstado"] == "Activo"


def test_history_filter_and_dispatch_queue_use_required_date_and_order_rules(
    db, monkeypatch
):
    now = datetime(2026, 11, 24, 12, 0)
    customer = add_user(
        db,
        user_id=38,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=21,
    )
    add_product(db)
    add_order(
        db,
        order_id=36,
        customer_id=21,
        product_id=1,
        created_at=datetime(2026, 11, 23, 8, 0),
    )
    add_order(
        db,
        order_id=37,
        customer_id=21,
        product_id=1,
        state=OrderState.LISTO.value,
        created_at=datetime(2026, 11, 24, 8, 0),
    )
    add_order(
        db,
        order_id=38,
        customer_id=21,
        product_id=1,
        state=OrderState.ENTREGADO.value,
        created_at=datetime(2026, 11, 24, 9, 0),
    )
    monkeypatch.setattr(OrderService, "_now", staticmethod(lambda: now))
    db.commit()

    history = OrderService.history_filter(
        db,
        customer,
        fecha_inicio=date(2026, 11, 24),
        fecha_fin=date(2026, 11, 24),
        page=1,
        page_size=20,
    )
    queue = OrderService.dispatch_queue(db)

    assert [item["idPedido"] for item in history["items"]] == [38, 37]
    assert [item["idPedido"] for item in queue] == [36, 37]

    with pytest.raises(OrderInvalidError, match="fechas futuras"):
        OrderService.history_filter(
            db,
            customer,
            fecha_inicio=date(2026, 11, 24),
            fecha_fin=date(2026, 11, 25),
            page=1,
            page_size=20,
        )


def test_status_transition_requires_assignment_and_follows_sequence(db, monkeypatch):
    now = datetime(2026, 11, 24, 11, 0)
    baker = add_user(
        db,
        user_id=24,
        role_id=3,
        role_name=UserRole.PANADERO.value,
    )
    add_user(
        db,
        user_id=25,
        role_id=4,
        role_name=UserRole.DOMICILIARIO.value,
        courier_id=70,
    )
    add_user(
        db,
        user_id=26,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=14,
    )
    add_product(db)
    order = add_order(
        db,
        order_id=31,
        customer_id=14,
        product_id=1,
        created_at=now - timedelta(hours=1),
    )
    monkeypatch.setattr(OrderService, "_now", staticmethod(lambda: now))
    db.commit()

    OrderService.update_status(
        db,
        order.idPedido,
        OrderStatusUpdate(nuevoEstado=OrderState.EN_PREPARACION),
        baker,
    )
    OrderService.update_status(
        db,
        order.idPedido,
        OrderStatusUpdate(nuevoEstado=OrderState.LISTO),
        baker,
    )
    with pytest.raises(OrderInvalidError):
        OrderService.update_status(
            db,
            order.idPedido,
            OrderStatusUpdate(nuevoEstado=OrderState.EN_CAMINO),
            baker,
        )
    response = OrderService.update_status(
        db,
        order.idPedido,
        OrderStatusUpdate(
            nuevoEstado=OrderState.EN_CAMINO,
            domiciliario_idDomiciliario=70,
        ),
        baker,
    )

    assert response["estadoPedido"] == OrderState.EN_CAMINO.value
    assert response["domiciliario_idDomiciliario"] == 70


def test_customer_cannot_read_another_customers_order(db):
    owner = add_user(
        db,
        user_id=27,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=15,
    )
    add_user(
        db,
        user_id=28,
        role_id=5,
        role_name=UserRole.CLIENTE.value,
        customer_id=16,
    )
    add_product(db)
    order = add_order(
        db,
        order_id=32,
        customer_id=16,
        product_id=1,
    )
    db.commit()

    with pytest.raises(OrderForbiddenError):
        OrderService.get_order_detail(db, order.idPedido, owner)


def test_order_api_requires_authentication_and_valid_pagination(db):
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as client:
        unauthorized = client.get("/api/v1/orders")
        assert unauthorized.status_code == 401

        customer = add_user(
            db,
            user_id=29,
            role_id=5,
            role_name=UserRole.CLIENTE.value,
            customer_id=17,
        )
        _ = customer.rol.nombre
        app.dependency_overrides[get_current_user] = lambda: customer
        invalid_pagination = client.get("/api/v1/orders", params={"page": 0})
        empty_order = client.post(
            "/api/v1/orders",
            json={
                "cliente_idCliente": 17,
                "listaProductos": [],
                "fechaHoraEntregaEstimada": "2026-12-01T10:00:00",
            },
        )
        invalid_quantity = client.post(
            "/api/v1/orders",
            json={
                "cliente_idCliente": 17,
                "listaProductos": [{"idProducto": 1, "cantidad": 0}],
                "fechaHoraEntregaEstimada": "2026-12-01T10:00:00",
            },
        )

    assert invalid_pagination.status_code == 422
    assert empty_order.status_code == 400
    assert invalid_quantity.status_code == 400


def test_customer_order_api_uses_authenticated_customer_when_id_is_omitted():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")

    with Session(engine) as db:
        app.dependency_overrides[get_db] = lambda: db
        customer = add_user(
            db,
            user_id=39,
            role_id=5,
            role_name=UserRole.CLIENTE.value,
            customer_id=22,
        )
        add_product(db)
        db.commit()
        app.dependency_overrides[get_current_user] = lambda: customer

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/orders",
                json={
                    "listaProductos": [{"idProducto": 1, "cantidad": 1}],
                    "fechaHoraEntregaEstimada": (
                        datetime.now() + timedelta(days=1)
                    ).isoformat(),
                },
            )

        assert response.status_code == 201
        order = db.get(Pedido, response.json()["idPedido"])
        assert order.cliente_idCliente == 22

    engine.dispose()
