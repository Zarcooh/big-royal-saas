"""
Utilidades de autenticación y autorización.

Proporciona decoradores y helpers para proteger rutas y
gestionar sesiones de usuario en el contexto multi-tenant.
"""

from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """
    Decorador que verifica que el usuario tenga una sesión activa.

    Si no hay sesión, redirige a la página de login con un mensaje.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session:
            flash("Debes iniciar sesión para acceder a esta página.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorador que verifica que el usuario tenga rol de Administrador.

    Debe usarse junto con @login_required.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("rol") != "Administrador":
            flash("No tienes permisos para acceder a esta sección.", "danger")
            return redirect(url_for("auth.dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def get_current_restaurante_id() -> str:
    """
    Retorna el restaurante_id del usuario en sesión.

    Returns:
        str: UUID del restaurante al que pertenece el usuario actual.

    Raises:
        ValueError: Si no hay sesión activa o falta restaurante_id.
    """
    if "restaurante_id" not in session:
        raise ValueError("No se encontró restaurante_id en la sesión. El usuario debe iniciar sesión.")
    return session["restaurante_id"]


def get_current_user_id() -> str:
    """
    Retorna el ID del usuario en sesión (UUID de Supabase Auth).

    Returns:
        str: UUID del usuario autenticado.
    """
    if "usuario_id" not in session:
        raise ValueError("No se encontró usuario_id en la sesión.")
    return session["usuario_id"]
