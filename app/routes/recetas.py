"""
CU-03: Gestionar Recetas
Blueprint de recetas — ver la receta de un producto y agregarle insumos.

RN03 / RF-INV-09: la tabla 'recetas' no tiene columna restaurante_id; el tenant
se deriva de productos.restaurante_id e insumos.restaurante_id. Por eso toda
operación valida primero que el producto y el insumo pertenezcan al restaurante
del usuario en sesión antes de tocar 'recetas'.
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
from app.utils.supabase_client import get_supabase

recetas_bp = Blueprint("recetas", __name__, url_prefix="/recetas")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _es_uuid(valor: str) -> bool:
    """Valida que un identificador recibido por request tenga formato UUID."""
    try:
        UUID(str(valor))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _producto_del_tenant(producto_id: str, restaurante_id: str):
    """Retorna el producto solo si pertenece al restaurante en sesión; None si no."""
    respuesta = (
        get_supabase()
        .table("productos")
        .select("id, nombre, precio")
        .eq("id", producto_id)
        .eq("restaurante_id", restaurante_id)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def _insumo_del_tenant(insumo_id: str, restaurante_id: str):
    """Retorna el insumo solo si pertenece al restaurante en sesión; None si no."""
    respuesta = (
        get_supabase()
        .table("insumos")
        .select("id, nombre, unidad")
        .eq("id", insumo_id)
        .eq("restaurante_id", restaurante_id)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def _listar_productos(restaurante_id: str):
    respuesta = (
        get_supabase()
        .table("productos")
        .select("id, nombre")
        .eq("restaurante_id", restaurante_id)
        .order("nombre")
        .execute()
    )
    return respuesta.data if respuesta.data else []


def _listar_insumos(restaurante_id: str):
    respuesta = (
        get_supabase()
        .table("insumos")
        .select("id, nombre, unidad")
        .eq("restaurante_id", restaurante_id)
        .order("nombre")
        .execute()
    )
    return respuesta.data if respuesta.data else []


def _receta_de(producto_id: str):
    """Filas de la receta con el insumo embebido. El producto ya fue validado."""
    respuesta = (
        get_supabase()
        .table("recetas")
        .select("id, cantidad_consumo, insumo_id, insumos(id, nombre, unidad)")
        .eq("producto_id", producto_id)
        .execute()
    )
    filas = respuesta.data if respuesta.data else []
    return sorted(filas, key=lambda f: (f.get("insumos") or {}).get("nombre", ""))


# ---------------------------------------------------------------------------
# VER RECETA (RF-INV-07)
# ---------------------------------------------------------------------------

@recetas_bp.route("/")
@login_required
@admin_required
def listar():
    """
    Muestra el selector de productos del restaurante y, si se indica
    ?producto_id=<uuid>, la receta de ese producto con su formulario de alta.
    """
    restaurante_id = get_current_restaurante_id()
    productos = _listar_productos(restaurante_id)

    producto_id = request.args.get("producto_id")
    producto = None
    receta = []
    insumos_disponibles = []

    if producto_id:
        # Un producto de otro restaurante devuelve el mismo mensaje que uno
        # inexistente, para no revelar su existencia (RN03).
        if _es_uuid(producto_id):
            producto = _producto_del_tenant(producto_id, restaurante_id)

        if producto is None:
            flash("El producto seleccionado no existe.", "danger")
            return redirect(url_for("recetas.listar"))

        receta = _receta_de(producto_id)
        ya_en_receta = {fila["insumo_id"] for fila in receta}
        insumos_disponibles = [
            insumo
            for insumo in _listar_insumos(restaurante_id)
            if insumo["id"] not in ya_en_receta
        ]

    return render_template(
        "recetas/listar.html",
        productos=productos,
        producto=producto,
        receta=receta,
        insumos_disponibles=insumos_disponibles,
    )


# ---------------------------------------------------------------------------
# AGREGAR INSUMO A LA RECETA (RF-INV-08)
# ---------------------------------------------------------------------------

@recetas_bp.route("/<uuid:producto_id>/insumos", methods=["POST"])
@login_required
@admin_required
def agregar_insumo(producto_id):
    """
    Agrega un insumo a la receta del producto, indicando la cantidad
    consumida por unidad vendida.

    RF-INV-09: producto e insumo deben pertenecer al mismo restaurante.
    RF-INV-10: un insumo no puede repetirse dentro de la misma receta.
    """
    producto_id = str(producto_id)
    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase()
    destino = url_for("recetas.listar", producto_id=producto_id)

    if _producto_del_tenant(producto_id, restaurante_id) is None:
        flash("El producto seleccionado no existe.", "danger")
        return redirect(url_for("recetas.listar"))

    insumo_id = request.form.get("insumo_id", "").strip()
    if not insumo_id or not _es_uuid(insumo_id):
        flash("Debes seleccionar un insumo válido.", "danger")
        return redirect(destino)

    if _insumo_del_tenant(insumo_id, restaurante_id) is None:
        flash("El insumo seleccionado no pertenece a este restaurante.", "danger")
        return redirect(destino)

    cantidad = request.form.get("cantidad_consumo", type=float)
    if cantidad is None or cantidad <= 0:
        flash("La cantidad de consumo debe ser un número mayor que cero.", "danger")
        return redirect(destino)

    duplicado = (
        supabase.table("recetas")
        .select("id")
        .eq("producto_id", producto_id)
        .eq("insumo_id", insumo_id)
        .execute()
    )
    if duplicado.data:
        flash("Ese insumo ya forma parte de la receta.", "warning")
        return redirect(destino)

    supabase.table("recetas").insert(
        {
            "producto_id": producto_id,
            "insumo_id": insumo_id,
            "cantidad_consumo": cantidad,
        }
    ).execute()

    flash("Insumo agregado a la receta.", "success")
    return redirect(destino)
