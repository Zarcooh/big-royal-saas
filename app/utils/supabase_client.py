"""
Cliente Singleton de Supabase.

Proporciona una instancia única del cliente de Supabase,
inicializada con las credenciales desde las variables de entorno.
"""

import os
from supabase import create_client, Client

_cliente: Client | None = None


def get_supabase() -> Client:
    """
    Retorna la instancia singleton del cliente de Supabase.

    La primera llamada inicializa el cliente con SUPABASE_URL y
    SUPABASE_ANON_KEY desde las variables de entorno.

    Returns:
        Client: Cliente de Supabase listo para usar.
    """
    global _cliente
    if _cliente is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL y SUPABASE_ANON_KEY deben estar definidas en el archivo .env"
            )
        _cliente = create_client(url, key)
    return _cliente
