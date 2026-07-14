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
    from app.routes.recetas import recetas_bp
    from app.routes.inventario import inventario_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(insumos_bp)
    app.register_blueprint(recetas_bp)
    app.register_blueprint(inventario_bp)

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
