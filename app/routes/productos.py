"""
Módulo Productos (CU-22..25 + gestión de receta CU-08/10/11/12)
Blueprint 'productos' (URL /productos) — catálogo de productos y, por cada
producto, la receta que define qué insumos consume por unidad vendida.

La página principal es un catálogo de PRODUCTOS al estilo del de insumos:
crear, editar y eliminar productos, y desde cada fila "Gestionar receta" para
armar/editar/quitar sus insumos. (La tabla de BD sigue llamándose 'recetas'.)

RN03 / RF-INV-09: la tabla 'recetas' no tiene columna restaurante_id; el tenant
se deriva de productos.restaurante_id e insumos.restaurante_id. Por eso toda
operación sobre recetas valida primero que el producto (y el insumo) pertenezcan
al restaurante del usuario en sesión.
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

productos_bp = Blueprint("productos", __name__, url_prefix="/productos")


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
        get_supabase_usuario()
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
        get_supabase_usuario()
        .table("insumos")
        .select("id, nombre, unidad")
        .eq("id", insumo_id)
        .eq("restaurante_id", restaurante_id)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def _listar_insumos(restaurante_id: str):
    respuesta = (
        get_supabase_usuario()
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
        get_supabase_usuario()
        .table("recetas")
        .select("id, cantidad_consumo, insumo_id, insumos(id, nombre, unidad)")
        .eq("producto_id", producto_id)
        .execute()
    )
    filas = respuesta.data if respuesta.data else []
    return sorted(filas, key=lambda f: (f.get("insumos") or {}).get("nombre", ""))


def _validar_precio(valor: str):
    """
    Convierte el precio del formulario. Devuelve (precio, error): uno de los dos
    siempre es None. Reglas iguales para crear y editar, para no divergir.
    """
    try:
        precio = float(valor)
    except (ValueError, TypeError):
        return None, "El precio debe ser un número válido."
    if precio < 0:
        return None, "El precio no puede ser negativo."
    return precio, None


# ---------------------------------------------------------------------------
# LISTAR — catálogo de productos con el estado de su receta (RF-INV-07)
# ---------------------------------------------------------------------------

@productos_bp.route("/")
@login_required
@admin_required
def listar():
    """
    Catálogo de productos del restaurante, cada uno con cuántos insumos tiene
    su receta. Admite filtro por nombre (?q=), igual que el de insumos.

    RN03: la consulta filtra por restaurante_id; el filtro por nombre se aplica
    después del de tenant, nunca en su lugar.
    """
    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase_usuario()

    q = request.args.get("q", "").strip()

    consulta = (
        supabase.table("productos")
        .select("id, nombre, precio")
        .eq("restaurante_id", restaurante_id)
    )
    if q:
        consulta = consulta.ilike("nombre", f"%{q}%")

    productos = consulta.order("nombre").execute().data or []

    # Cuántos insumos tiene la receta de cada producto, en UNA sola consulta.
    if productos:
        lineas = (
            supabase.table("recetas")
            .select("producto_id")
            .in_("producto_id", [p["id"] for p in productos])
            .execute()
            .data
            or []
        )
        conteo: dict[str, int] = {}
        for linea in lineas:
            conteo[linea["producto_id"]] = conteo.get(linea["producto_id"], 0) + 1
        for p in productos:
            p["num_insumos"] = conteo.get(p["id"], 0)

    return render_template("productos/listar.html", productos=productos, q=q)


# ---------------------------------------------------------------------------
# CREAR producto
# ---------------------------------------------------------------------------

@productos_bp.route("/crear", methods=["GET", "POST"])
@login_required
@admin_required
def crear():
    """
    Crea un producto (GET muestra el formulario, POST lo persiste).

    Tras crearlo se redirige a "Gestionar receta" del nuevo producto: un
    producto sin receta se vende sin descontar stock, así que lo natural es
    ofrecer de inmediato armarle la receta.

    RN03: el producto creado lleva siempre el restaurante_id de la sesión.
    """
    if request.method == "GET":
        return render_template("productos/crear.html")

    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase_usuario()

    nombre = request.form.get("nombre", "").strip()
    precio, error_precio = _validar_precio(request.form.get("precio", "0").strip())

    errores = []
    if not nombre:
        errores.append("El nombre del producto es obligatorio.")
    if error_precio:
        errores.append(error_precio)

    if errores:
        for error in errores:
            flash(error, "danger")
        return render_template("productos/crear.html")

    try:
        respuesta = (
            supabase.table("productos")
            .insert(
                {
                    "restaurante_id": restaurante_id,
                    "nombre": nombre,
                    "precio": precio,
                }
            )
            .execute()
        )
    except Exception as e:
        flash(f"Error al crear el producto: {str(e)}", "danger")
        return render_template("productos/crear.html")

    nuevo_id = respuesta.data[0]["id"] if respuesta.data else None
    flash(f"Producto «{nombre}» creado. Ahora agrégale insumos a su receta.", "success")

    if nuevo_id:
        return redirect(url_for("productos.gestionar", producto_id=nuevo_id))
    return redirect(url_for("productos.listar"))


# ---------------------------------------------------------------------------
# EDITAR producto (nombre y precio)
# ---------------------------------------------------------------------------

@productos_bp.route("/editar/<producto_id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar(producto_id: str):
    """
    Edita el nombre y el precio de un producto.

    RN03: lectura y escritura validan que el producto sea del restaurante en
    sesión. El precio nuevo NO reescribe el historial: detalle_ventas guarda el
    precio con el que se vendió (ver migración 006), así que cambiarlo aquí solo
    afecta a ventas futuras.
    """
    if not _es_uuid(producto_id):
        flash("El identificador del producto no es válido.", "danger")
        return redirect(url_for("productos.listar"))

    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase_usuario()

    producto = _producto_del_tenant(producto_id, restaurante_id)
    if producto is None:
        flash("El producto seleccionado no existe.", "danger")
        return redirect(url_for("productos.listar"))

    if request.method == "GET":
        return render_template("productos/editar.html", producto=producto)

    nombre = request.form.get("nombre", "").strip()
    precio, error_precio = _validar_precio(request.form.get("precio", "0").strip())

    errores = []
    if not nombre:
        errores.append("El nombre del producto es obligatorio.")
    if error_precio:
        errores.append(error_precio)

    if errores:
        for error in errores:
            flash(error, "danger")
        return render_template("productos/editar.html", producto=producto)

    try:
        (
            supabase.table("productos")
            .update({"nombre": nombre, "precio": precio})
            .eq("id", producto_id)
            .eq("restaurante_id", restaurante_id)
            .execute()
        )
        flash(f"Producto «{nombre}» actualizado.", "success")
    except Exception as e:
        flash(f"Error al actualizar el producto: {str(e)}", "danger")
        return render_template("productos/editar.html", producto=producto)

    return redirect(url_for("productos.listar"))


# ---------------------------------------------------------------------------
# ELIMINAR producto (arrastra su receta por ON DELETE CASCADE)
# ---------------------------------------------------------------------------

@productos_bp.route("/eliminar/<producto_id>", methods=["POST"])
@login_required
@admin_required
def eliminar(producto_id: str):
    """
    Elimina un producto y, en cascada, las líneas de su receta.

    NO se puede eliminar un producto que ya tiene ventas: detalle_ventas
    referencia productos(id) SIN cascade, así que la BD rechazaría el borrado
    con un error de clave foránea. Se comprueba antes para dar un mensaje claro
    y no romper el historial de ventas (que los reportes del CU-07 necesitan).

    RN03: el borrado valida que el producto sea del restaurante en sesión.
    """
    if not _es_uuid(producto_id):
        flash("El identificador del producto no es válido.", "danger")
        return redirect(url_for("productos.listar"))

    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase_usuario()

    producto = _producto_del_tenant(producto_id, restaurante_id)
    if producto is None:
        flash("El producto seleccionado no existe.", "danger")
        return redirect(url_for("productos.listar"))

    tiene_ventas = (
        supabase.table("detalle_ventas")
        .select("id")
        .eq("producto_id", producto_id)
        .limit(1)
        .execute()
        .data
    )
    if tiene_ventas:
        flash(
            "No se puede eliminar: el producto ya tiene ventas registradas. "
            "Puedes eliminar su receta o editar su precio.",
            "danger",
        )
        return redirect(url_for("productos.listar"))

    try:
        respuesta = (
            supabase.table("productos")
            .delete()
            .eq("id", producto_id)
            .eq("restaurante_id", restaurante_id)
            .execute()
        )
        if respuesta.data:
            flash(f"Producto «{producto['nombre']}» eliminado.", "success")
        else:
            flash("No se pudo eliminar el producto. Verifica que exista.", "warning")
    except Exception as e:
        flash(f"Error al eliminar el producto: {str(e)}", "danger")

    return redirect(url_for("productos.listar"))


# ---------------------------------------------------------------------------
# GESTIONAR RECETA — ver la receta del producto y su formulario de alta
# ---------------------------------------------------------------------------

@productos_bp.route("/<uuid:producto_id>/gestionar")
@login_required
@admin_required
def gestionar(producto_id):
    """
    Muestra la receta de un producto: sus insumos con la cantidad de consumo,
    el formulario para agregar uno nuevo y las acciones de editar/eliminar.
    """
    producto_id = str(producto_id)
    restaurante_id = get_current_restaurante_id()

    # Un producto de otro restaurante devuelve el mismo mensaje que uno
    # inexistente, para no revelar su existencia (RN03).
    producto = _producto_del_tenant(producto_id, restaurante_id)
    if producto is None:
        flash("El producto seleccionado no existe.", "danger")
        return redirect(url_for("productos.listar"))

    receta = _receta_de(producto_id)
    ya_en_receta = {fila["insumo_id"] for fila in receta}
    insumos_disponibles = [
        insumo
        for insumo in _listar_insumos(restaurante_id)
        if insumo["id"] not in ya_en_receta
    ]

    return render_template(
        "recetas/gestionar.html",
        producto=producto,
        receta=receta,
        insumos_disponibles=insumos_disponibles,
    )


# ---------------------------------------------------------------------------
# AGREGAR INSUMO A LA RECETA (RF-INV-08)
# ---------------------------------------------------------------------------

@productos_bp.route("/<uuid:producto_id>/insumos", methods=["POST"])
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
    supabase = get_supabase_usuario()
    destino = url_for("productos.gestionar", producto_id=producto_id)

    if _producto_del_tenant(producto_id, restaurante_id) is None:
        flash("El producto seleccionado no existe.", "danger")
        return redirect(url_for("productos.listar"))

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


# ---------------------------------------------------------------------------
# EDITAR LA CANTIDAD DE UNA LÍNEA DE LA RECETA
# ---------------------------------------------------------------------------

@productos_bp.route("/<uuid:producto_id>/insumos/<uuid:linea_id>/editar", methods=["POST"])
@login_required
@admin_required
def editar_insumo(producto_id, linea_id):
    """
    Cambia la cantidad de consumo de un insumo ya presente en la receta.

    Solo se toca la cantidad: cambiar el insumo de una línea equivale a
    borrarla y crear otra, y así el UNIQUE(producto_id, insumo_id) sigue
    siendo la única defensa contra duplicados (RF-INV-10).
    """
    producto_id = str(producto_id)
    linea_id = str(linea_id)
    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase_usuario()
    destino = url_for("productos.gestionar", producto_id=producto_id)

    # RN03: 'recetas' no tiene restaurante_id; el tenant se valida por el producto.
    if _producto_del_tenant(producto_id, restaurante_id) is None:
        flash("El producto seleccionado no existe.", "danger")
        return redirect(url_for("productos.listar"))

    cantidad = request.form.get("cantidad_consumo", type=float)
    if cantidad is None or cantidad <= 0:
        flash("La cantidad de consumo debe ser un número mayor que cero.", "danger")
        return redirect(destino)

    respuesta = (
        supabase.table("recetas")
        .update({"cantidad_consumo": cantidad})
        .eq("id", linea_id)
        # Acota la línea al producto ya validado: impide editar la receta de
        # otro producto (posiblemente de otro restaurante) pasando otro id.
        .eq("producto_id", producto_id)
        .execute()
    )

    if respuesta.data:
        flash("Cantidad actualizada.", "success")
    else:
        flash("Esa línea no pertenece a la receta de este producto.", "warning")

    return redirect(destino)


# ---------------------------------------------------------------------------
# ELIMINAR UN INSUMO DE LA RECETA
# ---------------------------------------------------------------------------

@productos_bp.route("/<uuid:producto_id>/insumos/<uuid:linea_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def eliminar_insumo(producto_id, linea_id):
    """Quita un insumo de la receta del producto."""
    producto_id = str(producto_id)
    linea_id = str(linea_id)
    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase_usuario()
    destino = url_for("productos.gestionar", producto_id=producto_id)

    if _producto_del_tenant(producto_id, restaurante_id) is None:
        flash("El producto seleccionado no existe.", "danger")
        return redirect(url_for("productos.listar"))

    respuesta = (
        supabase.table("recetas")
        .delete()
        .eq("id", linea_id)
        .eq("producto_id", producto_id)
        .execute()
    )

    if respuesta.data:
        flash("Insumo eliminado de la receta.", "success")
    else:
        flash("Esa línea no pertenece a la receta de este producto.", "warning")

    return redirect(destino)


# ---------------------------------------------------------------------------
# ELIMINAR LA RECETA COMPLETA (deja el producto, vacía sus líneas)
# ---------------------------------------------------------------------------

@productos_bp.route("/<uuid:producto_id>/receta/eliminar", methods=["POST"])
@login_required
@admin_required
def eliminar_receta(producto_id):
    """
    Borra todas las líneas de la receta del producto.

    El producto NO se elimina: queda vendible pero sin descuento automático
    de stock, que es el caso que el CU-06 trata como 'producto sin receta'
    (flujo alterno 2.1) y por el que avisa al Cajero antes de vender.
    """
    producto_id = str(producto_id)
    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase_usuario()
    destino = url_for("productos.gestionar", producto_id=producto_id)

    producto = _producto_del_tenant(producto_id, restaurante_id)
    if producto is None:
        flash("El producto seleccionado no existe.", "danger")
        return redirect(url_for("productos.listar"))

    respuesta = (
        supabase.table("recetas").delete().eq("producto_id", producto_id).execute()
    )

    if respuesta.data:
        flash(
            f"Receta de «{producto['nombre']}» eliminada "
            f"({len(respuesta.data)} insumo(s) retirado(s)).",
            "success",
        )
    else:
        flash("Este producto no tenía receta que eliminar.", "warning")

    return redirect(destino)
