"""
Cliente Singleton de Supabase.

Proporciona una instancia única del cliente de Supabase,
inicializada con las credenciales desde las variables de entorno.
"""

import os
from flask import session
from supabase import create_client, Client

_cliente: Client | None = None


def _credenciales() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL y SUPABASE_ANON_KEY deben estar definidas en el archivo .env"
        )
    return url, key


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
        url, key = _credenciales()
        _cliente = create_client(url, key)
    return _cliente


def get_supabase_usuario() -> Client:
    """
    Retorna un cliente NUEVO autenticado con el token del usuario en sesión.

    Por qué no sirve el singleton aquí: `get_supabase()` devuelve un cliente
    compartido por todo el proceso, y `auth.sign_in_with_password()` deja el
    token del último que inició sesión guardado dentro de ese objeto. Con dos
    usuarios a la vez, las peticiones de uno pueden viajar con el JWT del otro.

    Eso es indiferente mientras la app pase el restaurante_id a mano en cada
    consulta, pero NO lo es para `registrar_venta` (CU-06): esa RPC deduce el
    restaurante y el usuario desde `auth.uid()`, es decir, desde el token. Un
    token equivocado significa una venta atribuida a otro restaurante, que es
    justo lo que prohíbe la RN03.

    Returns:
        Client: Cliente que habla con Postgres como el usuario de la sesión.

    Raises:
        ValueError: Si no hay token en la sesión (usuario sin login).
    """
    token = session.get("access_token")
    if not token:
        raise ValueError("No hay access_token en la sesión. El usuario debe iniciar sesión.")

    url, key = _credenciales()
    cliente = create_client(url, key)
    cliente.postgrest.auth(token)
    return cliente
