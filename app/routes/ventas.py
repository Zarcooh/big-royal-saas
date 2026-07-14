"""
CU-06: Registrar Venta (auto-descuento de stock)
Blueprint de ventas — el Cajero registra la venta de un producto y el sistema
descuenta automáticamente el stock de los insumos según la receta configurada.

El descuento NO se hace desde aquí. Toda la operación (venta + detalle +
descuento de cada insumo + auditoría) ocurre dentro de la RPC transaccional
`registrar_venta` (ver migrations/006), tal como exige el RF-INV-40. Si falla
el descuento de un solo insumo, la base revierte la venta entera (flujo alterno
4.1 / RNF-REL-01): nunca queda media venta ni un inventario descuadrado.

RN03: el restaurante NO se toma del formulario ni de la sesión de Flask, sino
del token del usuario dentro de la RPC. Por eso aquí se usa
`get_supabase_usuario()` y no el cliente singleton.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from app.utils.auth import login_required, get_current_restaurante_id
from app.utils.supabase_client import get_supabase_usuario

ventas_bp = Blueprint("ventas", __name__, url_prefix="/ventas")

# Errores que la RPC lanza y su traducción para el Cajero. Cualquier otro se
# trata como fallo genérico: no exponemos detalles internos de la base.
ERRORES_RPC = {
    "STOCK_INSUFICIENTE": (
        "No hay stock suficiente de algún insumo para esa cantidad. "
        "No se registró la venta.",
        "danger",
    ),
    "PRODUCTO_NO_ENCONTRADO": ("El producto seleccionado no existe.", "danger"),
    "CANTIDAD_INVALIDA": ("La cantidad debe ser mayor que cero.", "danger"),
    "ROL_NO_AUTORIZADO": ("Tu rol no puede registrar ventas.", "danger"),
    "USUARIO_SIN_PERFIL": ("Tu usuario no tiene un restaurante asignado.", "danger"),
    "NO_AUTENTICADO": ("Tu sesión expiró. Vuelve a iniciar sesión.", "warning"),
}


def _productos_con_receta(restaurante_id: str):
    """
    Productos del restaurante, cada uno con los insumos que consume.

    Corresponde al paso 2 del CU-06: antes de confirmar, el Cajero ve qué
    insumos requiere el producto. Los productos sin receta se marcan para poder
    avisar (flujo alterno 2.1).
    """
    supabase = get_supabase_usuario()

    productos = (
        supabase.table("productos")
        .select("id, nombre, precio")
        .eq("restaurante_id", restaurante_id)
        .order("nombre")
        .execute()
        .data
        or []
    )
    if not productos:
        return []

    recetas = (
        supabase.table("recetas")
        .select("producto_id, cantidad_consumo, insumos(nombre, unidad, stock_actual)")
        .in_("producto_id", [p["id"] for p in productos])
        .execute()
        .data
        or []
    )

    por_producto: dict[str, list] = {}
    for linea in recetas:
        insumo = linea.get("insumos") or {}
        por_producto.setdefault(linea["producto_id"], []).append(
            {
                "nombre": insumo.get("nombre", "(insumo eliminado)"),
                "unidad": insumo.get("unidad", ""),
                "stock_actual": insumo.get("stock_actual", 0),
                "cantidad_consumo": linea["cantidad_consumo"],
            }
        )

    for p in productos:
        p["receta"] = por_producto.get(p["id"], [])

    return productos


@ventas_bp.route("/", methods=["GET"])
@login_required
def registrar():
    """Muestra el catálogo con su receta y el formulario de venta (CU-06, pasos 1-2)."""
    productos = _productos_con_receta(get_current_restaurante_id())

    # Resumen de la venta recién hecha, si venimos de un POST correcto.
    # Se guarda en la sesión y se consume aquí para poder redirigir tras el POST
    # (patrón Post/Redirect/Get) y que recargar la página no repita la venta.
    resumen = session.pop("ultima_venta", None)

    # Venta de un producto sin receta, a la espera de que el Cajero confirme.
    pendiente = session.get("venta_sin_receta")

    return render_template(
        "ventas/registrar.html",
        productos=productos,
        resumen=resumen,
        pendiente=pendiente,
    )


@ventas_bp.route("/", methods=["POST"])
@login_required
def confirmar():
    """
    Registra la venta y dispara el auto-descuento (CU-06, pasos 3-6).

    La validación autoritativa (tenant, stock, receta) vive en la RPC. Aquí solo
    se filtran entradas obviamente malas y se traduce el error al Cajero.
    """
    producto_id = request.form.get("producto_id", "").strip()
    cantidad = request.form.get("cantidad", type=float)
    # El Cajero ya vio la alerta de "producto sin receta" y decidió continuar.
    confirmar_sin_receta = request.form.get("confirmar_sin_receta") == "1"

    if not producto_id:
        flash("Debes seleccionar un producto.", "danger")
        return redirect(url_for("ventas.registrar"))

    if cantidad is None or cantidad <= 0:
        flash("La cantidad debe ser un número mayor que cero.", "danger")
        return redirect(url_for("ventas.registrar"))

    try:
        respuesta = (
            get_supabase_usuario()
            .rpc(
                "registrar_venta",
                {
                    "p_producto_id": producto_id,
                    "p_cantidad": cantidad,
                    "p_confirmar_sin_receta": confirmar_sin_receta,
                },
            )
            .execute()
        )
    except Exception as e:
        mensaje = str(e)

        # Flujo alterno 2.1: el producto no tiene receta. No es un error: se
        # avisa al Cajero y se le ofrece continuar, que es lo que pide el CU-06.
        if "PRODUCTO_SIN_RECETA" in mensaje:
            session["venta_sin_receta"] = {
                "producto_id": producto_id,
                "cantidad": cantidad,
            }
            flash(
                "Este producto no tiene receta configurada: la venta se registrará "
                "sin descontar stock. Confirma si quieres continuar.",
                "warning",
            )
            return redirect(url_for("ventas.registrar"))

        for clave, (texto, categoria) in ERRORES_RPC.items():
            if clave in mensaje:
                flash(texto, categoria)
                break
        else:
            flash("No se pudo registrar la venta. Inténtalo de nuevo.", "danger")

        return redirect(url_for("ventas.registrar"))

    session.pop("venta_sin_receta", None)

    # Paso 6: confirmar la venta y mostrar el stock ya actualizado.
    session["ultima_venta"] = _resumen_de(respuesta.data, producto_id, cantidad)

    flash("Venta registrada y stock actualizado.", "success")
    return redirect(url_for("ventas.registrar"))


def _resumen_de(venta_id, producto_id: str, cantidad: float) -> dict:
    """Datos de la venta recién registrada, con el stock ya descontado."""
    supabase = get_supabase_usuario()
    restaurante_id = get_current_restaurante_id()

    producto = (
        supabase.table("productos")
        .select("nombre, precio")
        .eq("id", producto_id)
        .eq("restaurante_id", restaurante_id)
        .execute()
        .data
    )
    producto = producto[0] if producto else {"nombre": "(desconocido)", "precio": 0}

    receta = (
        supabase.table("recetas")
        .select("cantidad_consumo, insumos(nombre, unidad, stock_actual)")
        .eq("producto_id", producto_id)
        .execute()
        .data
        or []
    )

    insumos = []
    for linea in receta:
        insumo = linea.get("insumos") or {}
        insumos.append(
            {
                "nombre": insumo.get("nombre", "(insumo eliminado)"),
                "unidad": insumo.get("unidad", ""),
                "descontado": linea["cantidad_consumo"] * cantidad,
                "stock_actual": insumo.get("stock_actual", 0),
            }
        )

    return {
        "venta_id": venta_id,
        "producto": producto["nombre"],
        "cantidad": cantidad,
        "total": (producto.get("precio") or 0) * cantidad,
        "insumos": insumos,
    }
