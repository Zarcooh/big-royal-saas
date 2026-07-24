from flask import Flask
from config import Config


def create_app():
    """Factory de la aplicación Flask."""
    Config.validate()

    app = Flask(__name__)
    app.config.from_object(Config)

    # Registrar Blueprints
    from app.routes.auth import auth_bp
    from app.routes.insumos import insumos_bp
    from app.routes.productos import productos_bp
    from app.routes.inventario import inventario_bp
    from app.routes.pedidos import pedidos_bp
    from app.routes.ventas import ventas_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.alertas import alertas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(insumos_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(alertas_bp)

    # Contador de alertas activas para el navbar (solo Administrador).
    # Defensivo: cualquier fallo (p. ej. token expirado) devuelve 0 y no rompe
    # el render de ninguna página.
    @app.context_processor
    def inyectar_alertas_activas():
        from flask import session

        if session.get("rol") != "Administrador" or not session.get("access_token"):
            return {"alertas_activas": 0}
        try:
            from app.utils.supabase_client import get_supabase_usuario
            from app.utils.auth import get_current_restaurante_id

            filas = (
                get_supabase_usuario()
                .table("alertas_stock")
                .select("id")
                .eq("restaurante_id", get_current_restaurante_id())
                .eq("atendida", False)
                .execute()
                .data
                or []
            )
            return {"alertas_activas": len(filas)}
        except Exception:
            return {"alertas_activas": 0}

    # Manejadores de error globales
    @app.errorhandler(404)
    def not_found(_error):
        from flask import render_template
        return render_template("error.html", codigo=404, mensaje="Página no encontrada."), 404

    @app.errorhandler(500)
    def internal_error(_error):
        from flask import render_template
        return render_template("error.html", codigo=500, mensaje="Error interno del servidor."), 500

    return app
