"""
CU-17 / RF-INV-18: Alertas de stock mínimo.

Muestra las alertas que la RPC de venta genera automáticamente cuando el stock
de un insumo cruza a su nivel mínimo tras el auto-descuento (ver migración 011).
El Administrador puede consultarlas y marcarlas como atendidas.

RN03: todas las consultas filtran por el restaurante de la sesión.
"""

from uuid import UUID

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from app.utils.auth import login_required, admin_required, get_current_restaurante_id
from app.utils.supabase_client import get_supabase_usuario

alertas_bp = Blueprint("alertas", __name__, url_prefix="/alertas")


def _es_uuid(valor: str) -> bool:
    try:
        UUID(str(valor))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


@alertas_bp.route("/")
@login_required
@admin_required
def listar():
    """Lista las alertas del restaurante. Por defecto solo las activas (?ver=todas para verlas todas)."""
    restaurante_id = get_current_restaurante_id()
    ver = request.args.get("ver", "activas")

    consulta = (
        get_supabase_usuario()
        .table("alertas_stock")
        .select(
            "id, stock_actual, stock_minimo, origen, atendida, creada_en, "
            "insumos(nombre, unidad)"
        )
        .eq("restaurante_id", restaurante_id)
    )
    if ver != "todas":
        consulta = consulta.eq("atendida", False)

    alertas = consulta.order("creada_en", desc=True).execute().data or []

    return render_template("alertas/listar.html", alertas=alertas, ver=ver)


@alertas_bp.route("/<alerta_id>/atender", methods=["POST"])
@login_required
@admin_required
def atender(alerta_id: str):
    """Marca una alerta como atendida (RN03 + RLS: solo el Admin del tenant)."""
    if not _es_uuid(alerta_id):
        flash("Identificador de alerta no válido.", "danger")
        return redirect(url_for("alertas.listar"))

    restaurante_id = get_current_restaurante_id()
    respuesta = (
        get_supabase_usuario()
        .table("alertas_stock")
        .update({"atendida": True})
        .eq("id", alerta_id)
        .eq("restaurante_id", restaurante_id)
        .execute()
    )

    if respuesta.data:
        flash("Alerta marcada como atendida.", "success")
    else:
        flash("No se pudo actualizar la alerta.", "warning")

    return redirect(url_for("alertas.listar"))
