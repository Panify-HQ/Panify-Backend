from io import BytesIO
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.infrastructure.database.session import get_db
from app.models.usuario import Usuario
from app.schemas.receipt import ReceiptDetail, ReceiptListResponse
from app.services.receipt_service import (
    ReceiptConflictError,
    ReceiptForbiddenError,
    ReceiptNotFoundError,
    ReceiptService,
)

router = APIRouter(prefix="/receipts", tags=["Receipts"])


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, ReceiptNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ReceiptForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(error),
    )


@router.get(
    "/",
    response_model=ReceiptListResponse,
    summary="RF-005.2 - Consultar recibos",
    operation_id="rf_005_2_consultar_recibos",
)
def list_receipts(
    search: str | None = Query(
        default=None,
        max_length=100,
        openapi_examples={
            "cliente": {"summary": "Buscar por nombre", "value": "Ana"},
            "producto": {"summary": "Buscar por producto", "value": "campesino"},
        },
    ),
    page: int = Query(
        default=1,
        ge=1,
        openapi_examples={
            "primera_pagina": {"summary": "Primera página", "value": 1},
            "segunda_pagina": {"summary": "Segunda página", "value": 2},
        },
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        openapi_examples={
            "veinte": {"summary": "Listar 20 recibos", "value": 20},
            "cincuenta": {"summary": "Listar 50 recibos", "value": 50},
        },
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    try:
        return ReceiptService.list_receipts(
            db=db,
            current_user=current_user,
            search=search,
            page=page,
            page_size=page_size,
        )
    except ReceiptForbiddenError as error:
        raise _http_error(error) from error


@router.get(
    "/{receipt_id}",
    response_model=ReceiptDetail,
    summary="RF-005.3 - Consultar detalle del recibo",
    operation_id="rf_005_3_detalle_recibo",
)
def get_receipt(
    receipt_id: int = Path(
        gt=0,
        openapi_examples={
            "recibo_101": {"summary": "Consultar recibo 101", "value": 101}
        },
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    try:
        return ReceiptService.get_receipt_detail(db, receipt_id, current_user)
    except (ReceiptNotFoundError, ReceiptForbiddenError, ReceiptConflictError) as error:
        raise _http_error(error) from error


@router.get(
    "/{receipt_id}/pdf",
    summary="RF-005.4 - Descargar recibo en PDF",
    operation_id="rf_005_4_descargar_recibo_pdf",
)
def download_receipt_pdf(
    receipt_id: int = Path(
        gt=0,
        openapi_examples={
            "recibo_101": {"summary": "Descargar PDF del recibo 101", "value": 101}
        },
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    try:
        receipt = ReceiptService.get_receipt_detail(db, receipt_id, current_user)
    except (ReceiptNotFoundError, ReceiptForbiddenError, ReceiptConflictError) as error:
        raise _http_error(error) from error

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Recibo {receipt['idRecibo']}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
    )
    right_style = ParagraphStyle(
        "ReceiptRight",
        parent=styles["Normal"],
        alignment=TA_RIGHT,
    )
    client = receipt["cliente"]
    order = receipt["pedido"]
    content = [
        Paragraph("Recibo de compra", title_style),
        Spacer(1, 8 * mm),
        Paragraph(f"<b>Recibo:</b> {receipt['idRecibo']}", styles["Normal"]),
        Paragraph(f"<b>Pedido:</b> {order['idPedido']}", styles["Normal"]),
        Paragraph(
            f"<b>Fecha de emisión:</b> {receipt['fechaEmision']:%Y-%m-%d %H:%M}",
            styles["Normal"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"<b>Cliente:</b> {escape(client['nombre'])} "
            f"{escape(client['apellido'])}",
            styles["Normal"],
        ),
        Paragraph(f"<b>Correo:</b> {escape(client['correo'])}", styles["Normal"]),
        Paragraph(f"<b>Teléfono:</b> {escape(client['telefono'])}", styles["Normal"]),
        Paragraph(
            f"<b>Dirección:</b> {escape(client['direccion'])}",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
    ]

    rows = [["Producto", "Cantidad", "Precio unitario", "Subtotal"]]
    for line in receipt["productos"]:
        rows.append(
            [
                Paragraph(escape(line["nombreProducto"]), styles["Normal"]),
                str(line["cantidad"]),
                f"${line['precioUnitario']:,.2f}",
                f"${line['subtotal']:,.2f}",
            ]
        )
    rows.append(
        [
            "",
            "",
            Paragraph("<b>Total</b>", right_style),
            f"${receipt['totalPagar']:,.2f}",
        ]
    )
    table = Table(rows, colWidths=[78 * mm, 22 * mm, 35 * mm, 35 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2E4D5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#3D2B1F")),
                ("GRID", (0, 0), (-1, -2), 0.3, colors.grey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("SPAN", (0, -1), (1, -1)),
                ("LINEABOVE", (2, -1), (-1, -1), 0.8, colors.black),
            ]
        )
    )
    content.append(table)
    document.build(content)
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="recibo-{receipt_id}.pdf"'
        },
    )
