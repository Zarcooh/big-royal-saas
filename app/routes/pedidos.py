"""
CU-05: Solicitar Insumos a Proveedor
Blueprint de pedidos — listar insumos críticos y generar órdenes de compra.

RN03: toda consulta filtra por restaurante_id del usuario en sesión.
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
from app.utils.auth import login_required, admin_required, get_current_restaurante_id, get_current_user_id
from app.utils.supabase_client import get_supabase, get_supabase_usuario

pedidos_bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _es_uuid(valor: str) -> bool:
    """Valida formato UUID."""
    try:
        UUID(str(valor))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _proveedores_del_tenant(restaurante_id: str):
    """Lista los proveedores del restaurante en sesión."""
    respuesta = (
        get_supabase_usuario()
        .table("proveedores")
        .select("id, nombre, telefono")
        .eq("restaurante_id", restaurante_id)
        .order("nombre")
        .execute()
    )
    return respuesta.data if respuesta.data else []


def _insumos_criticos(restaurante_id: str):
    """
    Retorna los insumos con stock_actual <= stock_minimo para el
    restaurante en sesión (RN03).

    Se filtra en Python porque Supabase/PostgREST no soporta
    comparaciones columna-a-columna en el DSL del SDK de Python.
    """
    respuesta = (
        get_supabase_usuario()
        .table("insumos")
        .select("id, nombre, unidad, stock_actual, stock_minimo")
        .eq("restaurante_id", restaurante_id)
        .order("nombre")
        .execute()
    )
    if not respuesta.data:
        return []
    return [r for r in respuesta.data if r["stock_actual"] <= r["stock_minimo"]]


# ---------------------------------------------------------------------------
# LISTAR insumos críticos y formulario de pedido
# ---------------------------------------------------------------------------

@pedidos_bp.route("/")
@login_required
@admin_required
def listar():
    """
    Muestra los insumos con stock crítico (stock_actual <= stock_minimo)
    y el formulario para generar una orden de compra.

    Flujo Alterno 2.1: si no hay insumos críticos, muestra el mensaje
    "Inventario en niveles óptimos".
    """
    restaurante_id = get_current_restaurante_id()
    criticos = _insumos_criticos(restaurante_id)
    proveedores = _proveedores_del_tenant(restaurante_id)

    return render_template(
        "pedidos/listar.html",
        criticos=criticos,
        proveedores=proveedores,
    )


# ---------------------------------------------------------------------------
# CREAR pedido
# ---------------------------------------------------------------------------

@pedidos_bp.route("/crear", methods=["POST"])
@login_required
@admin_required
def crear():
    """
    Crea una orden de pedido en estado 'Pendiente' (Flujo Básico paso 4)
    con los insumos críticos seleccionados y el proveedor indicado.

    RN03: restaurante_id siempre desde la sesión.
    """
    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase_usuario()

    proveedor_id = request.form.get("proveedor_id", "").strip()
    cantidades = request.form.getlist("cantidad")
    insumo_ids = request.form.getlist("insumo_id")

    # Validaciones
    if not proveedor_id or not _es_uuid(proveedor_id):
        flash("Debes seleccionar un proveedor válido.", "danger")
        return redirect(url_for("pedidos.listar"))

    # Filtrar solo líneas con cantidad > 0
    lineas = []
    for insumo_id, cantidad_str in zip(insumo_ids, cantidades):
        try:
            cantidad = float(cantidad_str)
        except (ValueError, TypeError):
            continue
        if cantidad > 0 and _es_uuid(insumo_id):
            lineas.append((insumo_id, cantidad))

    if not lineas:
        flash("Debes indicar al menos una cantidad mayor a cero.", "warning")
        return redirect(url_for("pedidos.listar"))

    try:
        # 1. Crear el pedido cabecera
        pedido_resp = (
            supabase.table("pedidos")
            .insert(
                {
                    "restaurante_id": restaurante_id,
                    "proveedor_id": proveedor_id,
                    "estado": "Pendiente",
                }
            )
            .execute()
        )

        if not pedido_resp.data:
            flash("No se pudo crear la orden de pedido.", "danger")
            return redirect(url_for("pedidos.listar"))

        pedido_id = pedido_resp.data[0]["id"]

        # 2. Insertar líneas de detalle
        for insumo_id, cantidad in lineas:
            (
                supabase.table("detalle_pedidos")
                .insert(
                    {
                        "pedido_id": pedido_id,
                        "insumo_id": insumo_id,
                        "cantidad": cantidad,
                    }
                )
                .execute()
            )

        flash(
            f"✓ Orden de pedido creada exitosamente en estado 'Pendiente'. {len(lineas)} insumo(s) solicitado(s).",
            "success",
        )
    except Exception as e:
        flash(f"Error al crear la orden de pedido: {str(e)}", "danger")

    return redirect(url_for("pedidos.listar"))
