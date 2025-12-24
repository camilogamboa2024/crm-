# 🚗 Gamboa Rental Cars - CRM

Sistema de gestión de relaciones con clientes (CRM) y administración de flota para la empresa de renta de vehículos **Gamboa Rental Cars**. Este proyecto permite gestionar el inventario de vehículos, reservas y clientes.

## 📋 Características

* **Gestión de Flota:** Control de vehículos (Picanto, Sonet, K3, etc.), estados (disponible, rentado) y precios.
* **Buscador:** Filtrado de vehículos por modelo o disponibilidad.
* **Gestión de Clientes:** Registro y administración de datos de clientes.
* **Reservas:** Sistema para crear y dar seguimiento a las reservas.

## 🛠️ Tecnologías

* **Python** 3.11+
* **Django** 4.2
* **HTML5 / CSS3** (Diseño responsivo)
* **SQLite** (Base de datos por defecto)

## 🚀 Instalación y Uso

Sigue estos pasos para correr el proyecto en tu máquina local:

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/camilogamboa2024/crm.git](https://github.com/camilogamboa2024/crm.git)
    cd crm
    ```

2.  **Crear y activar un entorno virtual:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Linux/Mac
    # .venv\Scripts\activate   # En Windows
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Aplicar migraciones:**
    ```bash
    python manage.py migrate
    ```

5.  **Correr el servidor:**
    ```bash
    python manage.py runserver
    ```

Visita `http://127.0.0.1:8000/` en tu navegador.

## 👤 Autor

**Christian Camilo Marmolejo Gamboa**
