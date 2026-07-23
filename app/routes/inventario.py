"""
CU-04: Ajustar Inventario Manualmente
Blueprint de ajustes de inventario — registrar mermas, pérdidas o ingresos
manuales para cuadrar el stock físico.

Toda operación se ejecuta mediante la función RPC transaccional
`registrar_ajuste_inventario` (ver migrations/002), que actualiza el stock y
registra el movimiento en auditoria_inventario dentro de una sola transacción.
Así se garantiza la auditoría obligatoria de CU-04: nunca hay un cambio de
stock sin su registro correspondiente.

RN03: el restaurante_id se toma siempre de la sesión, jamás del formulario.
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
from app.utils.auth import (
    login_required,
    admin_required,
    get_current_restaurante_id,
    get_current_user_id,
)
from app.utils.supabase_client import get_supabase_usuario

inventario_bp = Blueprint("inventario", __name__, url_prefix="/inventario")


# Vocabulario de tipos de operación y su efecto sobre el stock.
#   signo +1 -> suma al stock (entrada)
#   signo -1 -> resta del stock (salida)
# NOTA: si la columna auditoria_inventario.tipo_operacion tuviera un CHECK con
# valores distintos, basta con ajustar las claves de este diccionario.
TIPOS_OPERACION = {
    "ingreso": {"etiqueta": "Ingreso de mercadería", "signo": 1},
    "merma": {"etiqueta": "Merma", "signo": -1},
    "perdida": {"etiqueta": "Pérdida", "signo": -1},
}


def _es_uuid(valor: str) -> bool:
    try:
        UUID(str(valor))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _insumo_del_tenant(insumo_id: str, restaurante_id: str):
    """Retorna la ficha del insumo solo si pertenece al restaurante en sesión."""
    respuesta = (
        get_supabase_usuario()
        .table("insumos")
        .select("id, nombre, unidad, stock_actual, stock_minimo")
        .eq("id", insumo_id)
        .eq("restaurante_id", restaurante_id)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


@inventario_bp.route("/")
@login_required
@admin_required
def listar():
    """Buscador de insumos del restaurante para elegir cuál ajustar (CU-04, paso 1)."""
    restaurante_id = get_current_restaurante_id()
    q = request.args.get("q", "").strip()

    consulta = (
        get_supabase_usuario()
        .table("insumos")
        .select("id, nombre, unidad, stock_actual, stock_minimo")
        .eq("restaurante_id", restaurante_id)
    )
    if q:
        consulta = consulta.ilike("nombre", f"%{q}%")

    insumos = consulta.order("nombre").execute().data or []

    return render_template("inventario/listar.html", insumos=insumos, q=q)


@inventario_bp.route("/<uuid:insumo_id>/ajustar", methods=["GET", "POST"])
@login_required
@admin_required
def ajustar(insumo_id):
    """
    Muestra la ficha del insumo con su stock físico y aplica el ajuste (CU-04).

    El nuevo stock y el registro de auditoría se escriben de forma atómica en la
    función RPC; aquí solo se validan las entradas y se interpreta el resultado.
    """
    insumo_id = str(insumo_id)
    restaurante_id = get_current_restaurante_id()

    insumo = _insumo_del_tenant(insumo_id, restaurante_id)
    if insumo is None:
        # Inexistente o de otro restaurante: mismo mensaje (RN03).
        flash("El insumo seleccionado no existe.", "danger")
        return redirect(url_for("inventario.listar"))

    if request.method == "GET":
        return render_template(
            "inventario/ajustar.html", insumo=insumo, tipos=TIPOS_OPERACION
        )

    # --- POST: validar entradas ---
    destino = url_for("inventario.ajustar", insumo_id=insumo_id)

    tipo = request.form.get("tipo_operacion", "").strip()
    if tipo not in TIPOS_OPERACION:
        flash("Debes seleccionar un tipo de operación válido.", "danger")
        return redirect(destino)

    magnitud = request.form.get("cantidad", type=float)
    if magnitud is None or magnitud <= 0:
        flash("La cantidad debe ser un número mayor que cero.", "danger")
        return redirect(destino)

    motivo = request.form.get("motivo", "").strip()
    if not motivo:
        flash("Debes indicar el motivo del ajuste.", "danger")
        return redirect(destino)

    # La cantidad guardada lleva signo según el tipo de operación.
    cantidad_afectada = magnitud * TIPOS_OPERACION[tipo]["signo"]

    # Validación temprana en la app (la BD la revalida de forma autoritativa).
    if insumo["stock_actual"] + cantidad_afectada < 0:
        flash("Cantidad inválida: el ajuste dejaría el stock en negativo.", "danger")
        return redirect(destino)

    try:
        get_supabase_usuario().rpc(
            "registrar_ajuste_inventario",
            {
                "p_restaurante_id": restaurante_id,
                "p_insumo_id": insumo_id,
                "p_usuario_id": get_current_user_id(),
                "p_tipo_operacion": tipo,
                "p_cantidad_afectada": cantidad_afectada,
                "p_motivo": motivo,
            },
        ).execute()
    except Exception as e:
        mensaje = str(e)
        if "STOCK_NEGATIVO" in mensaje:
            flash("Cantidad inválida: el ajuste dejaría el stock en negativo.", "danger")
        elif "INSUMO_NO_ENCONTRADO" in mensaje:
            flash("El insumo seleccionado no existe.", "danger")
        elif "CANTIDAD_INVALIDA" in mensaje:
            flash("La cantidad debe ser un número distinto de cero.", "danger")
        else:
            flash("No se pudo registrar el ajuste. Inténtalo de nuevo.", "danger")
        return redirect(destino)

    flash("Ajuste registrado y auditado correctamente.", "success")
    return redirect(url_for("inventario.listar"))
