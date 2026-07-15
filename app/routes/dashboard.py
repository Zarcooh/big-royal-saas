"""
CU-07: Consultar Dashboard y Reportes
Blueprint de reportes — KPIs en tiempo real, tabla de consumo con filtro
por fecha y exportación a CSV.

RNF-INV-PER-03: indicadores de stock en tiempo real.
RNF-INV-PER-02: tabla de consumo con respuesta < 3 segundos.
RN03: todas las agregaciones filtran por restaurante_id.
"""

from datetime import datetime, date, timedelta
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    hoy = date.today().isoformat()  # "2026-07-14"

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


def _dia_siguiente(fecha_str: str) -> str:
    """
    Devuelve la fecha del día siguiente en ISO, para usarla como cota
    superior EXCLUSIVA en filtros sobre columnas TIMESTAMPTZ.

    'created_at' es TIMESTAMPTZ y las fechas del filtro llegan como
    'YYYY-MM-DD'. Comparar `created_at <= 'YYYY-MM-DD'` equivale a
    `<= las 00:00 de ese día`, así que dejaría fuera todas las ventas
    hechas durante el propio día 'hasta'. Usando `< día_siguiente` se
    incluye el día completo.
    """
    try:
        return (
            datetime.strptime(fecha_str, "%Y-%m-%d").date() + timedelta(days=1)
        ).isoformat()
    except (ValueError, TypeError):
        # Formato inesperado: se devuelve tal cual para no romper la consulta.
        return fecha_str


def _tabla_consumo(restaurante_id: str, desde: str, hasta: str):
    """
    Consulta la tabla de consumo de insumos por ventas en el rango
    de fechas indicado (RNF-INV-PER-02: respuesta < 3 segundos).
    """
    supabase = get_supabase_usuario()

    # Cota superior exclusiva: inicio del día siguiente a 'hasta' (ver
    # _dia_siguiente). Con `.lte("created_at", hasta)` se perderían las
    # ventas del propio día 'hasta'.
    ventas = (
        supabase.table("ventas")
        .select("id, total, created_at")
        .eq("restaurante_id", restaurante_id)
        .gte("created_at", desde)
        .lt("created_at", _dia_siguiente(hasta))
        .order("created_at", desc=True)
        .execute()
    )

    if not ventas.data:
        return []

    # Para cada venta, obtener sus detalles con joins
    filas = []
    for venta in ventas.data:
        detalles = (
            supabase.table("detalle_ventas")
            .select("cantidad, precio_unitario, productos(nombre)")
            .eq("venta_id", venta["id"])
            .execute()
        )

        if detalles.data:
            for det in detalles.data:
                producto_nombre = (
                    det["productos"]["nombre"]
                    if isinstance(det.get("productos"), dict)
                    else "—"
                )
                filas.append(
                    {
                        "venta_id": str(venta["id"])[:8],
                        "fecha": venta["created_at"][:19],
                        "producto": producto_nombre,
                        "cantidad": det["cantidad"],
                        "precio_unitario": det["precio_unitario"],
                        "subtotal": det["cantidad"] * det["precio_unitario"],
                        "total_venta": venta["total"],
                    }
                )

    return filas


# ---------------------------------------------------------------------------
# Dashboard / Reportes
# ---------------------------------------------------------------------------

@dashboard_bp.route("/")
@login_required
@admin_required
def index():
    """
    Muestra el dashboard con KPIs y el formulario de filtro por fecha.
    Si no hay historial de transacciones, muestra una advertencia.
    """
    restaurante_id = get_current_restaurante_id()

    if not _hay_historial(restaurante_id):
        flash(
            "⚠️ No hay historial de transacciones aún. Registre ventas o ajustes de inventario primero.",
            "warning",
        )
        # Aún mostramos los KPIs (todos en cero)
        kpis = _kpis(restaurante_id)
        return render_template("reportes/dashboard.html", kpis=kpis, filas=[], sin_historial=True)

    kpis = _kpis(restaurante_id)

    # Fechas por defecto: últimos 7 días
    hoy = date.today()
    desde = request.args.get("desde", hoy.replace(day=1).isoformat())
    hasta = request.args.get("hasta", hoy.isoformat())

    # Configurar el filtro para que solo aparezca al emitir reporte
    filas = []
    emitido = request.args.get("emitido", "0")

    return render_template(
        "reportes/dashboard.html",
        kpis=kpis,
        filas=filas,
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
    Flujo Básico paso 3: configura las fechas de filtro y emite el reporte.
    Flujo Básico paso 4: muestra mensaje de confirmación con cantidad de registros.
    """
    restaurante_id = get_current_restaurante_id()

    desde = request.form.get("desde", "").strip()
    hasta = request.form.get("hasta", "").strip()

    if not desde or not hasta:
        flash("Debes indicar ambas fechas para emitir el reporte.", "warning")
        return redirect(url_for("dashboard_rpt.index"))

    kpis = _kpis(restaurante_id)
    filas = _tabla_consumo(restaurante_id, desde, hasta)

    # Flujo Básico paso 4: mensaje de confirmación
    if filas:
        flash(
            f"✓ Reporte emitido correctamente. Se encontraron {len(filas)} registros.",
            "success",
        )
    else:
        flash(
            "✓ Reporte emitido. No se hallaron registros en el rango de fechas indicado.",
            "info",
        )

    return render_template(
        "reportes/dashboard.html",
        kpis=kpis,
        filas=filas,
        desde=desde,
        hasta=hasta,
        emitido="1",
        sin_historial=False,
    )


@dashboard_bp.route("/exportar", methods=["POST"])
@login_required
@admin_required
def exportar():
    """
    Exporta la tabla de consumo a CSV (funcionalidad opcional).
    """
    restaurante_id = get_current_restaurante_id()
    desde = request.form.get("desde", "").strip()
    hasta = request.form.get("hasta", "").strip()

    filas = _tabla_consumo(restaurante_id, desde, hasta)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Venta ID", "Fecha", "Producto", "Cantidad", "Precio Unit.", "Subtotal", "Total Venta"])
    for f in filas:
        writer.writerow([f["venta_id"], f["fecha"], f["producto"], f["cantidad"], f["precio_unitario"], f["subtotal"], f["total_venta"]])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=reporte_{desde}_a_{hasta}.csv"},
    )
