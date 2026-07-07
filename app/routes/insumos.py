"""
CU-02: Gestionar Catálogo de Insumos
Blueprint CRUD de insumos — listar, crear, editar y eliminar.
Implementa RN03: cada operación está acotada al restaurante_id del usuario en sesión.
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

insumos_bp = Blueprint("insumos", __name__, url_prefix="/insumos")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _columnas_relevantes() -> str:
    """Retorna las columnas exactas del modelo de insumos que nos interesan."""
    return "id, restaurante_id, nombre, unidad, stock_actual, stock_minimo"


# ---------------------------------------------------------------------------
# LISTAR
# ---------------------------------------------------------------------------

@insumos_bp.route("/")
@login_required
@admin_required
def listar():
    """
    Lista todos los insumos del restaurante del administrador autenticado.

    RN03: la consulta filtra explícitamente por restaurante_id para
    garantizar el aislamiento cross-tenant.
    """
    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase()

    respuesta = (
        supabase.table("insumos")
        .select(_columnas_relevantes())
        .eq("restaurante_id", restaurante_id)
        .order("nombre")
        .execute()
    )

    insumos = respuesta.data if respuesta.data else []

    return render_template("insumos/listar.html", insumos=insumos)


# ---------------------------------------------------------------------------
# CREAR
# ---------------------------------------------------------------------------

@insumos_bp.route("/crear", methods=["GET", "POST"])
@login_required
@admin_required
def crear():
    """
    Muestra el formulario de creación (GET) o persiste un nuevo insumo (POST).

    RN03: el registro creado incluye siempre el restaurante_id de la sesión.
    """
    if request.method == "GET":
        return render_template("insumos/crear.html")

    # ── POST ──────────────────────────────────────────────────────────
    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase()

    nombre = request.form.get("nombre", "").strip()
    unidad = request.form.get("unidad", "").strip()
    stock_actual = request.form.get("stock_actual", "0").strip()
    stock_minimo = request.form.get("stock_minimo", "0").strip()

    # Validaciones básicas del lado del servidor
    errores = []
    if not nombre:
        errores.append("El nombre del insumo es obligatorio.")
    if not unidad:
        errores.append("La unidad de medida es obligatoria.")
    try:
        stock_actual = float(stock_actual)
        if stock_actual < 0:
            errores.append("El stock actual no puede ser negativo.")
    except ValueError:
        errores.append("El stock actual debe ser un número válido.")
    try:
        stock_minimo = float(stock_minimo)
        if stock_minimo < 0:
            errores.append("El stock mínimo no puede ser negativo.")
    except ValueError:
        errores.append("El stock mínimo debe ser un número válido.")

    if errores:
        for error in errores:
            flash(error, "danger")
        return render_template("insumos/crear.html")

    try:
        (
            supabase.table("insumos")
            .insert(
                {
                    "restaurante_id": restaurante_id,
                    "nombre": nombre,
                    "unidad": unidad,
                    "stock_actual": stock_actual,
                    "stock_minimo": stock_minimo,
                }
            )
            .execute()
        )
        flash(f"Insumo «{nombre}» creado exitosamente.", "success")
    except Exception as e:
        flash(f"Error al crear el insumo: {str(e)}", "danger")
        return render_template("insumos/crear.html")

    return redirect(url_for("insumos.listar"))


# ---------------------------------------------------------------------------
# EDITAR
# ---------------------------------------------------------------------------

@insumos_bp.route("/editar/<id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar(id: str):
    """
    Muestra el formulario de edición precargado (GET) o guarda los cambios (POST).

    RN03: tanto la lectura como la escritura validan que el insumo
    pertenezca al restaurante del usuario en sesión.
    """
    # Validar que el ID tenga formato UUID
    try:
        UUID(id)
    except ValueError:
        flash("El identificador del insumo no es válido.", "danger")
        return redirect(url_for("insumos.listar"))

    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase()

    if request.method == "GET":
        respuesta = (
            supabase.table("insumos")
            .select(_columnas_relevantes())
            .eq("id", id)
            .eq("restaurante_id", restaurante_id)
            .maybe_single()
            .execute()
        )

        if not respuesta.data:
            flash("Insumo no encontrado o no pertenece a tu restaurante.", "warning")
            return redirect(url_for("insumos.listar"))

        return render_template("insumos/editar.html", insumo=respuesta.data)

    # ── POST ──────────────────────────────────────────────────────────
    nombre = request.form.get("nombre", "").strip()
    unidad = request.form.get("unidad", "").strip()
    stock_actual = request.form.get("stock_actual", "0").strip()
    stock_minimo = request.form.get("stock_minimo", "0").strip()

    errores = []
    if not nombre:
        errores.append("El nombre del insumo es obligatorio.")
    if not unidad:
        errores.append("La unidad de medida es obligatoria.")
    try:
        stock_actual = float(stock_actual)
        if stock_actual < 0:
            errores.append("El stock actual no puede ser negativo.")
    except ValueError:
        errores.append("El stock actual debe ser un número válido.")
    try:
        stock_minimo = float(stock_minimo)
        if stock_minimo < 0:
            errores.append("El stock mínimo no puede ser negativo.")
    except ValueError:
        errores.append("El stock mínimo debe ser un número válido.")

    if errores:
        for error in errores:
            flash(error, "danger")
        # Recargar datos del insumo para re-renderizar el formulario
        respuesta = (
            supabase.table("insumos")
            .select(_columnas_relevantes())
            .eq("id", id)
            .eq("restaurante_id", restaurante_id)
            .maybe_single()
            .execute()
        )
        return render_template("insumos/editar.html", insumo=respuesta.data)

    try:
        (
            supabase.table("insumos")
            .update(
                {
                    "nombre": nombre,
                    "unidad": unidad,
                    "stock_actual": stock_actual,
                    "stock_minimo": stock_minimo,
                }
            )
            .eq("id", id)
            .eq("restaurante_id", restaurante_id)
            .execute()
        )
        flash(f"Insumo «{nombre}» actualizado exitosamente.", "success")
    except Exception as e:
        flash(f"Error al actualizar el insumo: {str(e)}", "danger")

    return redirect(url_for("insumos.listar"))


# ---------------------------------------------------------------------------
# ELIMINAR
# ---------------------------------------------------------------------------

@insumos_bp.route("/eliminar/<id>", methods=["POST"])
@login_required
@admin_required
def eliminar(id: str):
    """
    Elimina un insumo. Solo se permite vía POST.

    RN03: la eliminación valida que el insumo pertenezca al
    restaurante del usuario autenticado.
    """
    try:
        UUID(id)
    except ValueError:
        flash("El identificador del insumo no es válido.", "danger")
        return redirect(url_for("insumos.listar"))

    restaurante_id = get_current_restaurante_id()
    supabase = get_supabase()

    try:
        respuesta = (
            supabase.table("insumos")
            .delete()
            .eq("id", id)
            .eq("restaurante_id", restaurante_id)
            .execute()
        )

        if respuesta.data:
            flash("Insumo eliminado exitosamente.", "success")
        else:
            flash("No se pudo eliminar el insumo. Verifica que exista y te pertenezca.", "warning")
    except Exception as e:
        flash(f"Error al eliminar el insumo: {str(e)}", "danger")

    return redirect(url_for("insumos.listar"))
