"""
CU-07: Consultar Dashboard y Reportes
Blueprint de reportes — KPIs en tiempo real y tres reportes con filtro por
fecha y exportación a CSV:

  * ventas   — cada venta con el detalle de productos que registró el Cajero.
  * ajustes  — ajustes de inventario (tipo de operación y motivo) del CU-04.
  * pedidos  — órdenes de compra a proveedor del CU-05, con sus insumos.

RNF-INV-PER-03: indicadores de stock en tiempo real.
RNF-INV-PER-02: tabla de consumo con respuesta < 3 segundos.
RN03: todas las agregaciones filtran por restaurante_id.
"""

from datetime import date
import csv
import io

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
)
from app.utils.auth import login_required, admin_required, get_current_restaurante_id
from app.utils.supabase_client import get_supabase_usuario

dashboard_bp = Blueprint("dashboard_rpt", __name__, url_prefix="/reportes")

# Pestañas disponibles y su etiqueta. La clave viaja en ?tab=.
PESTANAS = {
    "ventas": "🧾 Ventas",
    "ajustes": "📦 Ajustes de inventario",
    "pedidos": "🚚 Pedidos a proveedor",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fin_del_dia(hasta: str) -> str:
    """
    Convierte 'YYYY-MM-DD' en el último instante de ese día.

    Sin esto, comparar una columna TIMESTAMPTZ contra la fecha pelada equivale
    a las 00:00:00, y el reporte "hasta hoy" se comía todo lo registrado hoy:
    el caso más habitual, porque el Administrador consulta el día en curso.
    """
    return f"{hasta}T23:59:59" if hasta else hasta


def _hay_historial(restaurante_id: str) -> bool:
    """
    Pre-condición: verifica que exista al menos un registro en ventas
    o en auditoria_inventario para el restaurante actual.
    """
    supabase = get_supabase_usuario()
    ventas_check = (
        supabase.table("ventas")
        .select("id")
        .eq("restaurante_id", restaurante_id)
        .limit(1)
        .execute()
    )
    if ventas_check.data:
        return True

    auditoria_check = (
        supabase.table("auditoria_inventario")
        .select("id")
        .eq("restaurante_id", restaurante_id)
        .limit(1)
        .execute()
    )
    return bool(auditoria_check.data)


def _kpis(restaurante_id: str) -> dict:
    """
    Calcula los KPIs del dashboard para el restaurante en sesión (RN03).

    Retorna un diccionario con las métricas agregadas.
    """
    supabase = get_supabase_usuario()
    hoy = date.today().isoformat()  # "2026-07-22"

    # Ventas del día
    ventas_resp = (
        supabase.table("ventas")
        .select("total")
        .eq("restaurante_id", restaurante_id)
        .gte("created_at", hoy)
        .execute()
    )
    ventas_data = ventas_resp.data or []
    total_ventas = sum(row["total"] for row in ventas_data)
    num_ventas = len(ventas_data)

    # Insumos críticos (stock_actual <= stock_minimo)
    # Se filtra en Python porque Supabase/PostgREST no soporta
    # comparaciones columna-a-columna en el DSL del SDK.
    criticos_resp = (
        supabase.table("insumos")
        .select("id, stock_actual, stock_minimo")
        .eq("restaurante_id", restaurante_id)
        .execute()
    )
    num_criticos = (
        len([r for r in (criticos_resp.data or []) if r["stock_actual"] <= r["stock_minimo"]])
    )

    # Mermas del día
    mermas_resp = (
        supabase.table("auditoria_inventario")
        .select("cantidad_afectada")
        .eq("restaurante_id", restaurante_id)
        .eq("tipo_operacion", "merma")
        .gte("fecha", hoy)
        .execute()
    )
    mermas_data = mermas_resp.data or []
    total_mermas = abs(sum(row["cantidad_afectada"] for row in mermas_data))

    # Ingresos del día
    ingresos_resp = (
        supabase.table("auditoria_inventario")
        .select("cantidad_afectada")
        .eq("restaurante_id", restaurante_id)
        .eq("tipo_operacion", "ingreso")
        .gte("fecha", hoy)
        .execute()
    )
    ingresos_data = ingresos_resp.data or []
    total_ingresos = sum(row["cantidad_afectada"] for row in ingresos_data)

    # Total de insumos registrados
    total_insumos_resp = (
        supabase.table("insumos")
        .select("id")
        .eq("restaurante_id", restaurante_id)
        .execute()
    )
    total_insumos = len(total_insumos_resp.data) if total_insumos_resp.data else 0

    return {
        "total_ventas_dia": total_ventas,
        "num_ventas_dia": num_ventas,
        "num_criticos": num_criticos,
        "total_mermas_dia": total_mermas,
        "total_ingresos_dia": total_ingresos,
        "total_insumos": total_insumos,
    }


# ---------------------------------------------------------------------------
# Reporte: ventas con su detalle
# ---------------------------------------------------------------------------

def _tabla_ventas(restaurante_id: str, desde: str, hasta: str):
    """
    Ventas del periodo con el detalle de productos de cada una.

    Una venta del carrito lleva varios productos, así que el reporte devuelve
    una fila por VENTA con sus líneas anidadas: aplanarlo repetiría el total
    de la venta en cada línea y cualquiera que sumara esa columna obtendría un
    total inflado.

    El detalle se trae en UNA sola consulta por lote (RNF-INV-PER-02), no una
    por venta.
    """
    supabase = get_supabase_usuario()

    ventas = (
        supabase.table("ventas")
        .select("id, total, created_at")
        .eq("restaurante_id", restaurante_id)
        .gte("created_at", desde)
        .lte("created_at", _fin_del_dia(hasta))
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    if not ventas:
        return []

    detalles = (
        supabase.table("detalle_ventas")
        .select("venta_id, cantidad, precio_unitario, productos(nombre)")
        .in_("venta_id", [v["id"] for v in ventas])
        .execute()
        .data
        or []
    )

    por_venta: dict[str, list] = {}
    for det in detalles:
        producto = det.get("productos") or {}
        por_venta.setdefault(det["venta_id"], []).append(
            {
                "producto": producto.get("nombre", "—"),
                "cantidad": det["cantidad"],
                "precio_unitario": det["precio_unitario"],
                "subtotal": det["cantidad"] * det["precio_unitario"],
            }
        )

    filas = []
    for venta in ventas:
        lineas = sorted(por_venta.get(venta["id"], []), key=lambda l: l["producto"])
        filas.append(
            {
                "venta_id": str(venta["id"])[:8],
                "fecha": venta["created_at"][:19].replace("T", " "),
                "total": venta["total"],
                "num_items": len(lineas),
                "lineas": lineas,
            }
        )

    return filas


# ---------------------------------------------------------------------------
# Reporte: ajustes de inventario (CU-04)
# ---------------------------------------------------------------------------

def _tabla_ajustes(restaurante_id: str, desde: str, hasta: str):
    """
    Movimientos manuales de stock del periodo: tipo de operación y motivo.

    Excluye el tipo 'Venta': esos movimientos los escribe la RPC de venta y ya
    tienen su propio reporte. Aquí solo van los ajustes que alguien decidió a
    mano (merma, pérdida, ingreso de mercadería), que es lo que se audita.
    """
    supabase = get_supabase_usuario()

    movimientos = (
        supabase.table("auditoria_inventario")
        .select("fecha, tipo_operacion, cantidad_afectada, motivo, insumos(nombre, unidad)")
        .eq("restaurante_id", restaurante_id)
        .neq("tipo_operacion", "Venta")
        .gte("fecha", desde)
        .lte("fecha", _fin_del_dia(hasta))
        .order("fecha", desc=True)
        .execute()
        .data
        or []
    )

    filas = []
    for movimiento in movimientos:
        insumo = movimiento.get("insumos") or {}
        cantidad = movimiento["cantidad_afectada"]
        filas.append(
            {
                "fecha": (movimiento.get("fecha") or "")[:19].replace("T", " "),
                # El tipo se guarda en minúsculas ('merma', 'perdida', 'ingreso').
                "tipo": movimiento["tipo_operacion"].capitalize(),
                "insumo": insumo.get("nombre", "(insumo eliminado)"),
                "unidad": insumo.get("unidad", ""),
                "cantidad": cantidad,
                # El signo ya distingue entrada de salida (ver convención en 002).
                "es_entrada": cantidad > 0,
                "motivo": movimiento.get("motivo") or "—",
            }
        )

    return filas


# ---------------------------------------------------------------------------
# Reporte: pedidos a proveedor (CU-05)
# ---------------------------------------------------------------------------

def _tabla_pedidos(restaurante_id: str, desde: str, hasta: str):
    """
    Órdenes de compra del periodo con su proveedor y los insumos solicitados.

    Misma forma que el reporte de ventas: una fila por PEDIDO con sus líneas
    anidadas, y el detalle en una sola consulta por lote.
    """
    supabase = get_supabase_usuario()

    pedidos = (
        supabase.table("pedidos")
        .select("id, estado, fecha_creacion, proveedores(nombre, telefono)")
        .eq("restaurante_id", restaurante_id)
        .gte("fecha_creacion", desde)
        .lte("fecha_creacion", _fin_del_dia(hasta))
        .order("fecha_creacion", desc=True)
        .execute()
        .data
        or []
    )
    if not pedidos:
        return []

    detalles = (
        supabase.table("detalle_pedidos")
        .select("pedido_id, cantidad, insumos(nombre, unidad)")
        .in_("pedido_id", [p["id"] for p in pedidos])
        .execute()
        .data
        or []
    )

    por_pedido: dict[str, list] = {}
    for det in detalles:
        insumo = det.get("insumos") or {}
        por_pedido.setdefault(det["pedido_id"], []).append(
            {
                "insumo": insumo.get("nombre", "(insumo eliminado)"),
                "unidad": insumo.get("unidad", ""),
                "cantidad": det["cantidad"],
            }
        )

    filas = []
    for pedido in pedidos:
        proveedor = pedido.get("proveedores") or {}
        lineas = sorted(por_pedido.get(pedido["id"], []), key=lambda l: l["insumo"])
        filas.append(
            {
                "pedido_id": str(pedido["id"])[:8],
                "fecha": (pedido.get("fecha_creacion") or "")[:19].replace("T", " "),
                "proveedor": proveedor.get("nombre", "(proveedor eliminado)"),
                "telefono": proveedor.get("telefono") or "—",
                "estado": pedido.get("estado") or "—",
                "num_items": len(lineas),
                "lineas": lineas,
            }
        )

    return filas


# Cada pestaña declara de dónde saca sus filas y cómo se aplanan para el CSV.
# Mantener las dos cosas juntas evita que el reporte en pantalla y el
# exportado se separen con el tiempo.
def _filas_de(tab: str, restaurante_id: str, desde: str, hasta: str):
    if tab == "ajustes":
        return _tabla_ajustes(restaurante_id, desde, hasta)
    if tab == "pedidos":
        return _tabla_pedidos(restaurante_id, desde, hasta)
    return _tabla_ventas(restaurante_id, desde, hasta)


def _csv_de(tab: str, filas: list):
    """Devuelve (cabecera, filas planas) del reporte indicado."""
    if tab == "ajustes":
        cabecera = ["Fecha", "Tipo", "Insumo", "Cantidad", "Unidad", "Motivo"]
        return cabecera, [
            [f["fecha"], f["tipo"], f["insumo"], f["cantidad"], f["unidad"], f["motivo"]]
            for f in filas
        ]

    if tab == "pedidos":
        cabecera = ["Pedido", "Fecha", "Proveedor", "Estado", "Insumo", "Cantidad", "Unidad"]
        planas = []
        for pedido in filas:
            if not pedido["lineas"]:
                planas.append(
                    [pedido["pedido_id"], pedido["fecha"], pedido["proveedor"],
                     pedido["estado"], "—", 0, ""]
                )
            for linea in pedido["lineas"]:
                planas.append(
                    [pedido["pedido_id"], pedido["fecha"], pedido["proveedor"],
                     pedido["estado"], linea["insumo"], linea["cantidad"], linea["unidad"]]
                )
        return cabecera, planas

    cabecera = ["Venta", "Fecha", "Producto", "Cantidad", "Precio Unit.", "Subtotal", "Total Venta"]
    planas = []
    for venta in filas:
        if not venta["lineas"]:
            planas.append([venta["venta_id"], venta["fecha"], "—", 0, 0, 0, venta["total"]])
        for linea in venta["lineas"]:
            planas.append(
                [venta["venta_id"], venta["fecha"], linea["producto"], linea["cantidad"],
                 linea["precio_unitario"], linea["subtotal"], venta["total"]]
            )
    return cabecera, planas


def _rango_pedido():
    """Fechas del formulario, con el mes en curso por defecto."""
    hoy = date.today()
    desde = request.values.get("desde", "").strip() or hoy.replace(day=1).isoformat()
    hasta = request.values.get("hasta", "").strip() or hoy.isoformat()
    return desde, hasta


def _pestana_pedida() -> str:
    tab = request.values.get("tab", "ventas").strip()
    return tab if tab in PESTANAS else "ventas"


# ---------------------------------------------------------------------------
# Dashboard / Reportes
# ---------------------------------------------------------------------------

@dashboard_bp.route("/")
@login_required
@admin_required
def index():
    """
    Muestra los KPIs, el filtro por fecha y, si ya se emitió el reporte
    (?emitido=1), la tabla de la pestaña seleccionada.

    El filtro viaja por la URL para que cambiar de pestaña conserve el rango
    de fechas sin tener que volver a emitir el reporte.
    """
    restaurante_id = get_current_restaurante_id()
    kpis = _kpis(restaurante_id)

    if not _hay_historial(restaurante_id):
        flash(
            "⚠️ No hay historial de transacciones aún. Registre ventas o ajustes de inventario primero.",
            "warning",
        )
        # Aún mostramos los KPIs (todos en cero)
        return render_template(
            "reportes/dashboard.html",
            kpis=kpis,
            filas=[],
            tab="ventas",
            pestanas=PESTANAS,
            sin_historial=True,
        )

    desde, hasta = _rango_pedido()
    tab = _pestana_pedida()
    emitido = request.args.get("emitido", "0")

    filas = _filas_de(tab, restaurante_id, desde, hasta) if emitido == "1" else []

    return render_template(
        "reportes/dashboard.html",
        kpis=kpis,
        filas=filas,
        tab=tab,
        pestanas=PESTANAS,
        desde=desde,
        hasta=hasta,
        emitido=emitido,
        sin_historial=False,
    )


@dashboard_bp.route("/generar", methods=["POST"])
@login_required
@admin_required
def generar():
    """
    Flujo Básico paso 3: emite el reporte con las fechas indicadas.

    Redirige a index con el rango en la URL (patrón Post/Redirect/Get) para
    que recargar o cambiar de pestaña no reenvíe el formulario.
    """
    desde = request.form.get("desde", "").strip()
    hasta = request.form.get("hasta", "").strip()

    if not desde or not hasta:
        flash("Debes indicar ambas fechas para emitir el reporte.", "warning")
        return redirect(url_for("dashboard_rpt.index"))

    if desde > hasta:
        flash("La fecha 'desde' no puede ser posterior a la fecha 'hasta'.", "warning")
        return redirect(url_for("dashboard_rpt.index"))

    return redirect(
        url_for(
            "dashboard_rpt.index",
            desde=desde,
            hasta=hasta,
            tab=_pestana_pedida(),
            emitido="1",
        )
    )


@dashboard_bp.route("/exportar", methods=["POST"])
@login_required
@admin_required
def exportar():
    """Exporta a CSV el reporte de la pestaña activa."""
    restaurante_id = get_current_restaurante_id()
    desde, hasta = _rango_pedido()
    tab = _pestana_pedida()

    filas = _filas_de(tab, restaurante_id, desde, hasta)
    cabecera, planas = _csv_de(tab, filas)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(cabecera)
    writer.writerows(planas)

    output.seek(0)
    return Response(
        # BOM para que Excel en Windows abra el CSV con los acentos correctos.
        "﻿" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment;filename=reporte_{tab}_{desde}_a_{hasta}.csv"
        },
    )
