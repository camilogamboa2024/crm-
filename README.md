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
- `static/` → assets (logo, imágenes, js/css si aplica)

---

## ⚙️ Requisitos

- **Python 3.11+**
- **Django 4.2.x**
- **SQLite** (incluida por defecto en Python)

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
pip install "Django>=4.2,<5.0"

# 4) Migraciones + cargar data inicial
python manage.py makemigrations crm
python manage.py migrate
python manage.py loaddata crm/fixtures/initial_cars.json

# 5) Crear superusuario (CRM/Admin)
python manage.py createsuperuser

# 6) Ejecutar el servidor
python manage.py runserver


👥 Equipo

Christian Camilo Marmolejo Gamboa — Founder / Dev

Stiben García Cartagena — Developer