import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuración base de la aplicación."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-por-defecto-insegura")

    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    @classmethod
    def validate(cls):
        """Valida que las variables de entorno obligatorias estén definidas."""
        missing = []
        if not cls.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not cls.SUPABASE_ANON_KEY:
            missing.append("SUPABASE_ANON_KEY")
        if missing:
            raise ValueError(
                f"Faltan las siguientes variables de entorno en .env: {', '.join(missing)}"
            )
