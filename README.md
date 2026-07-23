# Big Royal SaaS

Sistema web de **abastecimiento e inventario** para un restaurante, con control
de stock, recetas, ventas con auto-descuento y reportes. Multi-tenant: cada
restaurante solo ve y opera sus propios datos (aislamiento por `restaurante_id`
reforzado con políticas RLS en Supabase).

Proyecto universitario (INSO). Backend en **Flask** + **Supabase** (PostgreSQL).

---

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Puesta en marcha](#puesta-en-marcha)
- [Variables de entorno (`.env`)](#variables-de-entorno-env)
- [Cuentas de prueba](#cuentas-de-prueba)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Base de datos y migraciones](#base-de-datos-y-migraciones)
- [Flujo de trabajo con Git](#flujo-de-trabajo-con-git)
- [Documentación](#documentación)

---

## Requisitos

- **Python 3.12+** (probado en 3.14).
- Una cuenta/proyecto de **Supabase** ya aprovisionado (URL + clave anon).
- Git.

Dependencias (ver `requirements.txt`): Flask, supabase, python-dotenv, Werkzeug,
gunicorn.

---

## Puesta en marcha

```bash
# 1. Clonar el repositorio (trae TODAS las ramas y su historial)
git clone https://github.com/Zarcooh/big-royal-saas.git
cd big-royal-saas

# 2. Crear y activar el entorno virtual
python -m venv .venv
#   Windows (PowerShell):
.venv\Scripts\Activate.ps1
#   macOS / Linux:
#   source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno (ver la sección siguiente)
copy .env.example .env      # Windows
# cp .env.example .env       # macOS / Linux
#   ...y rellena SUPABASE_URL y SUPABASE_ANON_KEY

# 5. Ejecutar
python run.py
```

La app queda en **http://127.0.0.1:5000**.

> **Nota (Windows + Python 3.14):** `run.py` incluye un *workaround* para una
> consulta WMI de `platform.system()` que puede colgar el arranque. Si usas ese
> entorno, ejecuta con el intérprete del venv: `.venv\Scripts\python.exe run.py`.

---

## Variables de entorno (`.env`)

El archivo `.env` **no está en el repositorio** (está en `.gitignore`). Copia
`.env.example` a `.env` y rellena los valores; el responsable del proyecto te
pasa las claves por un canal privado.

| Variable | ¿Necesaria? | Descripción |
|---|---|---|
| `SUPABASE_URL` | Sí | URL del proyecto Supabase. |
| `SUPABASE_ANON_KEY` | Sí | Clave publicable/anon. Es la única clave que usa la app; está protegida por RLS. |
| `SUPABASE_SERVICE_ROLE_KEY` | No | Secreto de administrador que **se salta RLS**. La app no lo usa. **No lo compartas ni lo subas al repo.** |

---

## Cuentas de prueba

Restaurante **Big Royal Centro**. Ambas con contraseña definida en Supabase Auth:

| Rol | Correo |
|---|---|
| Administrador | `jose@bigroyal.com` |
| Cajero | `cajero@bigroyal.com` |

El acceso a cada interfaz depende del **rol** del usuario, no de la URL.

---

## Estructura del proyecto

```
app/
  routes/        Blueprints por caso de uso (auth, insumos, recetas,
                 inventario, pedidos, ventas, dashboard/reportes)
  templates/     Vistas Jinja2
  static/        CSS / JS
  utils/         Cliente Supabase, helpers de auth y tenant
migrations/      Scripts SQL de esquema, RPC y políticas RLS (001..009)
docs/            Documentación (resumen de cambios para el informe)
config.py        Carga de configuración desde el entorno
run.py           Punto de entrada
```

---

## Base de datos y migraciones

El esquema, las funciones (RPC) y las políticas RLS viven en `migrations/`
(numeradas `001`..`009`). Se aplican **en orden** sobre el proyecto Supabase.
Una base a medio migrar (por RLS) deniega en silencio: ejecuta la cadena
completa.

Resumen: `001` esquema base · `002` RPC de ajuste de inventario · `003` tabla
usuarios · `004`/`005` políticas RLS · `006` ventas + RPC de venta · `007`
auditoría de accesos · `008` RPC de venta multi-ítem · `009` política UPDATE de
recetas.

No se necesita instalar Postgres localmente: la app se conecta al proyecto
Supabase configurado en el `.env`.

---

## Flujo de trabajo con Git

- La rama de integración es **`develop`**. `main` es la rama por defecto/estable.
- Para trabajar en algo, crea una rama desde `develop` y abre un **Pull Request**
  hacia `develop`.

```bash
git fetch origin
git checkout develop
git pull                 # traer lo último
git checkout -b feature/mi-cambio
# ...commits...
git push -u origin feature/mi-cambio
# luego abre el PR hacia develop en GitHub
```

Para ponerte al día con lo que otros mergearon:

```bash
git checkout develop
git pull
```

> Con un solo `git clone` ya tienes todas las ramas; no se clona rama por rama.
> Si no ves cambios recientes, te falta `git fetch` + `git pull` sobre `develop`.

---

## Documentación

- `docs/cambios-informe.md` — resumen por caso de uso de las mejoras recientes
  (redacción actualizada, requisitos funcionales propuestos y nota de base de
  datos), pensado para el informe final.
