"""
CU-01: Iniciar Sesión
Blueprint de autenticación — login, logout y dashboard por rol.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils.supabase_client import get_supabase
from app.utils.auth import login_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    """Redirige según el estado de la sesión."""
    if "usuario" in session:
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Maneja el formulario de inicio de sesión con Supabase Auth."""
    if request.method == "GET":
        return render_template("login.html")

    # POST: procesar credenciales
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Por favor, ingresa tu correo y contraseña.", "warning")
        return render_template("login.html")

    try:
        supabase = get_supabase()
        auth_response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

        if not auth_response.user:
            flash("Credenciales inválidas. Intenta de nuevo.", "danger")
            return render_template("login.html")

        usuario_id = auth_response.user.id

        # Obtener perfil y restaurante asociado desde la tabla 'usuarios'
        perfil_response = (
            supabase.table("usuarios")
            .select("id, restaurante_id, rol")
            .eq("id", usuario_id)
            .single()
            .execute()
        )

        if not perfil_response.data:
            flash("No se encontró un perfil asociado a este usuario.", "danger")
            return render_template("login.html")

        perfil = perfil_response.data

        # Establecer sesión Flask
        session["usuario"] = email
        session["usuario_id"] = usuario_id
        session["restaurante_id"] = perfil["restaurante_id"]
        session["rol"] = perfil["rol"]
        session["access_token"] = auth_response.session.access_token

        flash(f"Bienvenido, {email}.", "success")
        return redirect(url_for("auth.dashboard"))

    except Exception as e:
        flash(f"Error al iniciar sesión: {str(e)}", "danger")
        return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    """Renderiza el dashboard según el rol del usuario."""
    rol = session.get("rol", "")
    if rol == "Administrador":
        return render_template("dashboard/admin.html")
    elif rol == "Cajero":
        return render_template("dashboard/cajero.html")
    else:
        flash("Rol de usuario no reconocido.", "warning")
        return redirect(url_for("auth.logout"))
