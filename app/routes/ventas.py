"""
CU-06: Registrar Venta (carrito + auto-descuento de stock)
Blueprint de ventas — el Cajero arma un pedido con varios productos y, al
confirmarlo, el sistema descuenta automáticamente el stock de los insumos
según la receta de cada producto.

El descuento NO se hace desde aquí. Toda la operación (venta + detalle +
descuento de cada insumo + auditoría) ocurre dentro de la RPC transaccional
`registrar_venta_multiple` (ver migrations/008), tal como exige el RF-INV-40.
Si falla el descuento de un solo insumo, la base revierte la venta entera
(flujo alterno 4.1 / RNF-REL-01): nunca queda medio pedido cobrado ni un
inventario descuadrado.

EL CARRITO VIVE EN LA SESIÓN, no en el navegador: se guarda solo
{producto_id: cantidad}. El nombre, el precio y la receta se releen de la
base en cada render, así que un carrito abierto no puede cobrar el precio de
ayer ni mostrar un stock viejo. El precio autoritativo, de todos modos, lo
pone la RPC.

RN03: el restaurante NO se toma del formulario ni de la sesión de Flask, sino
del token del usuario dentro de la RPC. Por eso aquí se usa
`get_supabase_usuario()` y no el cliente singleton.
"""

from uuid import UUID

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
        "No hay stock suficiente de algún insumo para ese pedido. "
        "No se registró la venta.",
        "danger",
    ),
    "PRODUCTO_NO_ENCONTRADO": ("Algún producto del pedido ya no existe.", "danger"),
    "CANTIDAD_INVALIDA": ("Las cantidades deben ser mayores que cero.", "danger"),
    "PRODUCTO_SIN_RECETA": (
        "Algún producto del pedido no tiene receta configurada y no se puede "
        "vender. Quítalo del pedido o pide al Administrador que le defina su receta.",
        "danger",
    ),
    "CARRITO_VACIO": ("El pedido no tiene productos.", "warning"),
    "ROL_NO_AUTORIZADO": ("Tu rol no puede registrar ventas.", "danger"),
    "USUARIO_SIN_PERFIL": ("Tu usuario no tiene un restaurante asignado.", "danger"),
    "NO_AUTENTICADO": ("Tu sesión expiró. Vuelve a iniciar sesión.", "warning"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _es_uuid(valor: str) -> bool:
    try:
        UUID(str(valor))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _carrito() -> dict:
    """El pedido en curso: {producto_id: cantidad}."""
    return session.get("carrito", {})


def _guardar_carrito(carrito: dict) -> None:
    """
    Persiste el carrito. Se reasigna la clave entera en vez de mutar el dict
    en sitio porque Flask solo detecta el cambio de la sesión al asignar.
    """
    if carrito:
        session["carrito"] = carrito
    else:
        # Un carrito vacío y "sin carrito" son el mismo estado; no dejamos basura.
        session.pop("carrito", None)


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


def _lineas_del_carrito(productos: list, carrito: dict):
    """
    Cruza el carrito de la sesión con el catálogo recién leído de la base.

    Devuelve (líneas, huérfanos). Un producto que el Administrador borró
    mientras el Cajero armaba el pedido queda como huérfano: se retira del
    carrito en vez de dejar que la RPC rechace el pedido entero con
    PRODUCTO_NO_ENCONTRADO sin decir cuál era.
    """
    catalogo = {p["id"]: p for p in productos}
    lineas = []
    huerfanos = []

    for producto_id, cantidad in carrito.items():
        producto = catalogo.get(producto_id)
        if producto is None:
            huerfanos.append(producto_id)
            continue
        precio = producto.get("precio") or 0
        lineas.append(
            {
                "producto_id": producto_id,
                "nombre": producto["nombre"],
                "precio": precio,
                "cantidad": cantidad,
                "subtotal": precio * cantidad,
                "sin_receta": not producto["receta"],
            }
        )

    return lineas, huerfanos


# ---------------------------------------------------------------------------
# PANTALLA DE VENTA (CU-06, pasos 1-2)
# ---------------------------------------------------------------------------

@ventas_bp.route("/", methods=["GET"])
@login_required
def registrar():
    """Muestra el catálogo con su receta y el detalle del pedido en curso."""
    productos = _productos_con_receta(get_current_restaurante_id())

    carrito = _carrito()
    lineas, huerfanos = _lineas_del_carrito(productos, carrito)

    if huerfanos:
        for producto_id in huerfanos:
            carrito.pop(producto_id, None)
        _guardar_carrito(carrito)
        flash(
            "Se quitaron del pedido productos que ya no están en el catálogo.",
            "warning",
        )

    # Comprobante de la venta recién hecha, si venimos de un POST correcto.
    # Se guarda en la sesión y se consume aquí para poder redirigir tras el POST
    # (patrón Post/Redirect/Get) y que recargar la página no repita la venta.
    resumen = session.pop("ultima_venta", None)

    return render_template(
        "ventas/registrar.html",
        productos=productos,
        lineas=lineas,
        total=sum(linea["subtotal"] for linea in lineas),
        resumen=resumen,
    )


# ---------------------------------------------------------------------------
# CARRITO
# ---------------------------------------------------------------------------

@ventas_bp.route("/carrito/agregar", methods=["POST"])
@login_required
def agregar_al_carrito():
    """Suma un producto al pedido en curso (o incrementa su cantidad)."""
    producto_id = request.form.get("producto_id", "").strip()
    cantidad = request.form.get("cantidad", type=float)

    if not _es_uuid(producto_id):
        flash("Debes seleccionar un producto válido.", "danger")
        return redirect(url_for("ventas.registrar"))

    if cantidad is None or cantidad <= 0:
        flash("La cantidad debe ser un número mayor que cero.", "danger")
        return redirect(url_for("ventas.registrar"))

    carrito = _carrito()
    carrito[producto_id] = carrito.get(producto_id, 0) + cantidad
    _guardar_carrito(carrito)

    flash("Producto agregado al pedido.", "success")
    return redirect(url_for("ventas.registrar"))


@ventas_bp.route("/carrito/actualizar", methods=["POST"])
@login_required
def actualizar_carrito():
    """Fija la cantidad de una línea del pedido."""
    producto_id = request.form.get("producto_id", "").strip()
    cantidad = request.form.get("cantidad", type=float)

    carrito = _carrito()
    if not _es_uuid(producto_id) or producto_id not in carrito:
        flash("Ese producto no está en el pedido.", "warning")
        return redirect(url_for("ventas.registrar"))

    if cantidad is None or cantidad <= 0:
        flash("La cantidad debe ser un número mayor que cero.", "danger")
        return redirect(url_for("ventas.registrar"))

    carrito[producto_id] = cantidad
    _guardar_carrito(carrito)

    flash("Cantidad actualizada.", "success")
    return redirect(url_for("ventas.registrar"))


@ventas_bp.route("/carrito/quitar", methods=["POST"])
@login_required
def quitar_del_carrito():
    """Saca un producto del pedido en curso."""
    producto_id = request.form.get("producto_id", "").strip()

    carrito = _carrito()
    if carrito.pop(producto_id, None) is None:
        flash("Ese producto no está en el pedido.", "warning")
    else:
        _guardar_carrito(carrito)
        flash("Producto quitado del pedido.", "success")

    return redirect(url_for("ventas.registrar"))


@ventas_bp.route("/carrito/vaciar", methods=["POST"])
@login_required
def vaciar_carrito():
    """Descarta el pedido completo sin registrarlo."""
    _guardar_carrito({})
    flash("Pedido cancelado.", "info")
    return redirect(url_for("ventas.registrar"))


# ---------------------------------------------------------------------------
# CONFIRMAR LA COMPRA (CU-06, pasos 3-6)
# ---------------------------------------------------------------------------

@ventas_bp.route("/", methods=["POST"])
@login_required
def confirmar():
    """
    Registra la venta del carrito completo y dispara el auto-descuento.

    La validación autoritativa (tenant, precios, stock, receta) vive en la RPC.
    Aquí solo se filtran entradas obviamente malas y se traduce el error.
    """
    carrito = _carrito()
    if not carrito:
        flash("Agrega al menos un producto al pedido.", "warning")
        return redirect(url_for("ventas.registrar"))

    items = [
        {"producto_id": producto_id, "cantidad": cantidad}
        for producto_id, cantidad in carrito.items()
    ]

    try:
        respuesta = (
            get_supabase_usuario()
            .rpc("registrar_venta_multiple", {"p_items": items})
            .execute()
        )
    except Exception as e:
        mensaje = str(e)

        # Un producto sin receta bloquea la venta completa: no se puede vender
        # algo que no descuente stock (regla reforzada en la migración 010).
        for clave, (texto, categoria) in ERRORES_RPC.items():
            if clave in mensaje:
                flash(texto, categoria)
                break
        else:
            flash("No se pudo registrar la venta. Inténtalo de nuevo.", "danger")

        return redirect(url_for("ventas.registrar"))

    # Paso 6: confirmar la venta y mostrar el stock ya actualizado.
    session["ultima_venta"] = _resumen_de(respuesta.data)
    _guardar_carrito({})

    flash("Venta registrada y stock actualizado.", "success")
    return redirect(url_for("ventas.registrar"))


def _resumen_de(venta_id) -> dict:
    """
    Comprobante de la venta recién registrada, leído de la base.

    Se relee en vez de reconstruirse desde el carrito para que refleje lo que
    realmente quedó grabado: los precios que aplicó la RPC y el stock ya
    descontado. Los insumos salen del log de auditoría que la propia RPC
    escribió para esta venta, así que el comprobante y la auditoría no pueden
    contradecirse.
    """
    supabase = get_supabase_usuario()

    venta = (
        supabase.table("ventas")
        .select("total, created_at")
        .eq("id", venta_id)
        .execute()
        .data
    )
    venta = venta[0] if venta else {"total": 0, "created_at": ""}

    detalle = (
        supabase.table("detalle_ventas")
        .select("cantidad, precio_unitario, productos(nombre)")
        .eq("venta_id", venta_id)
        .execute()
        .data
        or []
    )

    lineas = []
    for fila in detalle:
        producto = fila.get("productos") or {}
        lineas.append(
            {
                "producto": producto.get("nombre", "(producto eliminado)"),
                "cantidad": fila["cantidad"],
                "precio_unitario": fila["precio_unitario"],
                "subtotal": fila["cantidad"] * fila["precio_unitario"],
            }
        )
    lineas.sort(key=lambda l: l["producto"])

    movimientos = (
        supabase.table("auditoria_inventario")
        .select("cantidad_afectada, insumos(nombre, unidad, stock_actual, stock_minimo)")
        .eq("motivo", f"Venta {venta_id}")
        .execute()
        .data
        or []
    )

    insumos = []
    for movimiento in movimientos:
        insumo = movimiento.get("insumos") or {}
        stock_actual = insumo.get("stock_actual", 0)
        stock_minimo = insumo.get("stock_minimo", 0)
        insumos.append(
            {
                "nombre": insumo.get("nombre", "(insumo eliminado)"),
                "unidad": insumo.get("unidad", ""),
                "descontado": abs(movimiento["cantidad_afectada"]),
                "stock_actual": stock_actual,
                # RF-INV-18: marca los insumos que quedaron en o bajo su mínimo,
                # para avisar al Cajero en el mismo comprobante.
                "en_alerta": stock_minimo is not None and stock_actual <= stock_minimo,
            }
        )
    insumos.sort(key=lambda i: i["nombre"])

    return {
        "venta_id": str(venta_id),
        "fecha": (venta.get("created_at") or "")[:19].replace("T", " "),
        "total": venta.get("total") or 0,
        "lineas": lineas,
        "insumos": insumos,
    }
