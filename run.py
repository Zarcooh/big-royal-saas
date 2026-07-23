"""
Big Royal SaaS — Punto de entrada de la aplicación.

Ejecutar con (usando el entorno virtual):
    .venv\\Scripts\\python.exe run.py
"""

# ── Workaround Windows + Python 3.14 ──────────────────────────────────
# `import supabase` llama a platform.system(); en Python 3.14 sobre
# Windows eso resuelve la versión del SO con una consulta WMI que en
# algunas máquinas se cuelga y bloquea todo el arranque. Deshabilitamos
# SOLO esa consulta (el resto de `platform` sigue igual) antes de que se
# importe supabase. Es inofensivo fuera de Windows.
import sys

if sys.platform == "win32":
    import platform as _platform

    def _no_wmi(*_args, **_kwargs):
        raise OSError("WMI deshabilitado (workaround Py3.14/Windows)")

    _platform._wmi_query = _no_wmi
# ──────────────────────────────────────────────────────────────────────

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
