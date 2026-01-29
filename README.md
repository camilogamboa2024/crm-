# 🚗 Gamboa Rental Cars — Web + CRM (Django)

Sistema completo para **Gamboa Rental Cars** que incluye:

- 🌐 **Sitio público**: Home, buscador de vehículos (`/buscar/`), checkout de reserva estilo “Multialquileres”.
- 🧠 **CRM / Panel interno**: administración de flota, clientes y reservas.
- 🧾 **Contrato**: vista pública del contrato (`/contrato/`).

> Proyecto local actual: **`gamboa_site (2)`**  
> Stack: **Django 4.2 + HTML + Bootstrap/Tailwind (CDN) + SQLite (dev)**

---

## ✨ Funcionalidades principales

### Sitio público
- ✅ **Home** (`/`) con branding y acceso rápido.
- ✅ **Buscador tipo rentadora** (`/buscar/`)
  - Búsqueda por fechas y pickup
  - Filtros por marca y rango de precio
  - Cálculo de total por días
- ✅ **Reserva pública (Checkout)** (`/crm/public/reserve/`)
  - Formulario de conductor (izquierda)
  - Resumen de reserva (derecha): días, tarifa, subtotal, ITBMS 7%, total
  - Valida disponibilidad (si el carro ya está reservado en esas fechas)
- ✅ **Confirmación de reserva** (`/crm/public/reserve/success/`)

### CRM (Panel interno)
- ✅ **Flota**: crear/editar vehículos, tarifa diaria, estado, placa.
- ✅ **Clientes**: crear/editar clientes.
- ✅ **Reservas**: crear/editar reservas, estado.
- ✅ Rutas claras y separadas del sitio público.

---

## 🧱 Estructura del proyecto

- `gamboa_project/` → configuración del proyecto Django (urls, settings, wsgi/asgi)
- `crm/` → app principal del CRM (models, forms, views, urls)
- `templates/` → templates públicos (home, search, contrato, etc.)
- `crm/templates/crm/` → templates del CRM y checkout público
- `static/` → assets organizados en `vendor/` (terceros) y `custom/` (proyecto)

---

## ⚙️ Requisitos

- **Python 3.11+**
- **Django 4.2.x**
- **SQLite** (incluida por defecto en Python)

---

## 🧰 Solución proxy 403 / instalación offline

Si tu entorno bloquea descargas (proxy 403) o no tiene internet, usa este flujo.

### Diagnóstico rápido (proxy)

```bash
env | grep -i proxy
pip config list -v
```

Si tienes un proxy, configura `pip`:

```ini
# ~/.config/pip/pip.conf (Linux/macOS) o %APPDATA%\\pip\\pip.ini (Windows)
[global]
proxy = http://usuario:password@proxy-host:puerto
```

### Instalación offline con wheelhouse

**En una máquina con internet:**

```bash
mkdir -p wheelhouse
python -m pip download -r requirements.txt -d wheelhouse
tar -czf wheelhouse.tar.gz wheelhouse requirements.txt
```

**En la máquina sin internet:**

```bash
tar -xzf wheelhouse.tar.gz
pip install --no-index --find-links wheelhouse -r requirements.txt
```

---

## 🚀 Instalación y ejecución (Local) — INSTRUCCIONES COMPLETAS (TODO JUNTO)

> Nota: si en tu repo NO existe `requirements.txt`, instala Django directo como aparece abajo.

```bash
# 1) Clonar repo
git clone https://github.com/camilogamboa2024/crm-.git
cd "gamboa_site (2)"  # si tu carpeta local se llama así

# 2) Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install --upgrade pip

# 3) Instalar dependencias
pip install -r requirements.txt

# 4) Configurar variables de entorno (solo una vez)
cp .env.example .env
# Edita .env con tu DJANGO_SECRET_KEY y DEBUG=1

# 5) Migraciones + cargar data inicial
python manage.py makemigrations crm
python manage.py migrate
python manage.py loaddata crm/fixtures/initial_cars.json

# 6) Crear superusuario (CRM/Admin)
python manage.py createsuperuser

# 7) Ejecutar el servidor
python manage.py runserver

```

## 🔧 Configuración .env (local y producción)

Crea un archivo `.env` en la raíz con valores como:

```bash
DJANGO_SECRET_KEY="reemplaza-por-una-clave-segura"
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://usuario:password@localhost:5432/gamboa
CSRF_TRUSTED_ORIGINS=http://localhost:8000
WHATSAPP_NUMBER=50762969414
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
SECURE_HSTS_SECONDS=0
AXES_FAILURE_LIMIT=5
AXES_COOLOFF_TIME=1
```

## 🔐 Seguridad básica (hardening)

Configura estas variables de entorno antes de pasar a producción:

- `DJANGO_DEBUG=0`
- `DJANGO_ALLOWED_HOSTS=tu-dominio.com`
- `CSRF_TRUSTED_ORIGINS=https://tu-dominio.com`
- `SECURE_SSL_REDIRECT=true`
- `SESSION_COOKIE_SECURE=true`
- `CSRF_COOKIE_SECURE=true`
- `SECURE_HSTS_SECONDS=31536000`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS=true`
- `SECURE_HSTS_PRELOAD=true`
- `SECURE_REFERRER_POLICY=same-origin`
- `X_FRAME_OPTIONS=DENY`
- `AXES_FAILURE_LIMIT=5`
- `AXES_COOLOFF_TIME=1`

Incluido:
- Rate limiting para `/buscar/` y `/crm/public/reserve/`.
- Protección anti-bruteforce en `/admin/` con `django-axes`.

## 🔐 Roles y acceso al CRM

El CRM usa grupos simples:

- **admin**: acceso total + dashboard + Django Admin (requiere `is_staff`).
- **staff**: crear/editar vehículos, clientes y reservas.
- **viewer**: solo lectura.

Los grupos se crean automáticamente al ejecutar `python manage.py migrate`.
Asigna el grupo desde el panel `/admin/` (Usuarios → Grupos).

## ✅ Política de disponibilidad

La **disponibilidad real** se calcula por reservas activas (no canceladas).  
El campo `Car.status` se usa para bloquear vehículos en **mantenimiento**, pero no para saber si están reservados.

## 🚀 Deploy en Render (PostgreSQL)

**Build Command**

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
```

**Start Command**

```bash
gunicorn gamboa_project.wsgi:application
```

Variables mínimas:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=0`
- `DJANGO_ALLOWED_HOSTS=tu-app.onrender.com`
- `DATABASE_URL` (Render la provee automáticamente)
- `CSRF_TRUSTED_ORIGINS=https://tu-app.onrender.com`

## 🐳 Docker (local prod-like)

```bash
docker compose up --build
```

El `docker-compose.yml` levanta PostgreSQL y Django con Gunicorn.

Ejemplo de `.env` para Docker:

```bash
DJANGO_SECRET_KEY=dev-secret
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://gamboa:gamboa@db:5432/gamboa
CSRF_TRUSTED_ORIGINS=http://localhost:8000
```

## ✅ Checklist de despliegue (MVP production-ready)

1. Exporta variables de entorno anteriores y un `DJANGO_SECRET_KEY` seguro.
2. Ejecuta `python manage.py collectstatic`.
3. Corre migraciones: `python manage.py migrate`.
4. Crea superusuario y asigna el grupo `admin` o `staff` según corresponda.
5. Verifica acceso público: `/`, `/buscar/`, `/crm/public/reserve/`.
6. Verifica acceso CRM (solo staff): `/crm/` y `/admin/`.
7. Ejecuta `python manage.py check --deploy` en producción.
8. Configura envío real de correo (SMTP) si deseas notificaciones.

## 🧪 Tests

Ejecuta:

```bash
pytest
```

### Prueba manual de concurrencia (recomendada)

1. Abre dos sesiones navegando al checkout público con el mismo auto y fechas.
2. Envía la primera reserva.
3. En la segunda sesión intenta confirmar la reserva inmediatamente.
4. Debe responder con error de disponibilidad (evita doble booking).

## 🧾 PDF de contratos (ReportLab)

Se usa `reportlab` para generar PDFs sin dependencias nativas complejas en producción.

👥 Equipo

Christian Camilo Marmolejo Gamboa — Founder / Dev

Stiben García Cartagena — Developer

CI check trigger
