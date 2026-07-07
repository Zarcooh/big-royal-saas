"""
Utilidad de validación Cross-Tenant (RN03).

Garantiza que cada operación sobre datos esté acotada al
restaurante del usuario autenticado, evitando fugas de
información entre tenants.
"""

from flask import session


def validar_pertenencia_restaurante(
    restaurante_id_solicitado: str
) -> bool:
    """
    Verifica que el restaurante_id solicitado coincida con el
    restaurante del usuario en sesión (RN03 — Aislamiento Cross-tenant).

    Args:
        restaurante_id_solicitado (str): UUID del restaurante contra el que se quiere operar.

    Returns:
        bool: True si el usuario pertenece a ese restaurante.

    Raises:
        ValueError: Si no hay sesión activa.
    """
    if "restaurante_id" not in session:
        raise ValueError("Sesión no inicializada. El usuario debe autenticarse primero.")

    return session["restaurante_id"] == restaurante_id_solicitado
