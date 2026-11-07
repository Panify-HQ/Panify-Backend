# Panify — Backend

> **"Horneamos Calidad, Entregamos Confianza y Unimos Lazos."**

Backend de **Panify**, el sistema de gestión de pedidos, inventario, recibos y entregas de **Distribuciones Oro Pan**, una fábrica de pan. Centraliza la lógica de negocio y el acceso a los datos de la plataforma web, reemplazando el registro manual de pedidos (llamadas y papel).

> 🚧 **Estado del proyecto:** en construcción. Por ahora el repositorio contiene la **estructura base** del backend (configuración, conexión a MySQL y verificación de estado). Los endpoints de cada módulo se agregarán en las siguientes etapas.

---

## 📌 Contexto

|                               |                                                                                             |
| ----------------------------- | ------------------------------------------------------------------------------------------- |
| **Cliente / caso de estudio** | Distribuciones Oro Pan (fábrica de pan)                                                     |
| **Programa**                  | SENA — Análisis y Desarrollo de Software (ADSO)                                             |
| **Ficha / Grupo**             | 3315796 / Grupo 4                                                                           |
| **Alcance**                   | Sistema operativo de pedidos y stock. No cubre procesos contables ni financieros complejos. |

**Problema:** los pedidos se toman de forma manual, lo que causa pérdida de información, retrasos en producción, confusiones para el domiciliario y falta de comprobantes claros para el cliente.

---

## 🎯 Objetivo del backend

Proveer la lógica de negocio, las reglas de validación y la persistencia que necesita el frontend para gestionar pedidos, inventario, recibos y entregas.

---

## 📦 Módulos

| Módulo                     | Responsabilidad                                                                                                                              |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Autenticación**          | Inicio de sesión y control de acceso por rol.                                                                                                |
| **Gestión de Usuarios**    | Registro, recuperación de contraseña y perfil con historial.                                                                                 |
| **Productos e Inventario** | CRUD del catálogo, stock mínimo, alertas de producto agotado y descuento automático del inventario al confirmar un pedido.                   |
| **Gestión de Pedidos**     | Creación de pedidos validados contra el stock disponible y control horario (bloqueo de pedidos para el mismo día después de la hora límite). |
| **Gestión de Recibos**     | Comprobante por cada pedido, con precios congelados al momento de la compra, y reportes operativos (diarios, semanales y mensuales).         |
| **Entregas y Rutas**       | Panel de prioridades ordenado por hora y urgencia, y lista de rutas simplificada para el panadero y el domiciliario.                         |

---

## 👤 Roles

| Rol                     | Descripción                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Cliente**             | Realiza pedidos.                                                                                                    |
| **Panadero**            | Registra la producción y actualiza el stock.                                                                        |
| **Domiciliario**        | Entrega los pedidos.                                                                                                |
| **Administrador**       | Mismos permisos que el Super Administrador, pero no puede gestionar a otros administradores ni otorgarse más poder. |
| **Super Administrador** | Control total del sistema; puede crear administradores.                                                             |

---

## 🗄️ Base de datos

- **Motor:** MySQL (modelo relacional normalizado hasta la **3FN**).
- **Modelado inicial:** MySQL Workbench.
- **Tablas y migraciones:** las tablas se definen como modelos con **SQLAlchemy** y se crean mediante **Alembic**.
- **Control de acceso:** especialización de `USUARIO` en `CLIENTE`, `DOMICILIARIO` y `PANADERO`.
- **Entidades principales:** `USUARIO`, `CLIENTE`, `DOMICILIARIO`, `PANADERO`, `DIRECCION`, `PRODUCTO`, `PEDIDO`, `DETALLE_PEDIDO`, `RECIBO`.
- **Valores derivados (calculados, no almacenados):** total a pagar, subtotal y estado de stock.

---

## 🛠️ Tecnologías

| Componente                 | Tecnología                   |
| -------------------------- | ---------------------------- |
| Lenguaje                   | Python                       |
| Framework                  | FastAPI                      |
| Servidor                   | Uvicorn                      |
| Base de datos              | MySQL                        |
| ORM y conexión             | SQLAlchemy 2 + PyMySQL       |
| Migraciones                | Alembic                      |
| Validación y configuración | Pydantic / pydantic-settings |
| Pruebas                    | Pytest + HTTPX               |
| Control de versiones       | Git y GitHub                 |

**Pendiente por definir:** mecanismo de autenticación y manejo de sesiones, cifrado de contraseñas, librería para generar recibos en PDF y estrategia de despliegue.

---

## 🚀 Instalación y ejecución

### Requisitos previos

- Python 3.12 o superior
- MySQL en ejecución, con una base de datos vacía creada para Panify

### Pasos

**1. Verificar e instalar Python**

Se recomienda utilizar **Python 3.13.x** para garantizar una mejor compatibilidad con las dependencias del proyecto.

Verifica tu versión de Python:

```bash
python --version
```

Si tienes varias versiones instaladas, puedes consultar las disponibles con:

```bash
py --list
```

**Importante:** Si tienes Python 3.15, utiliza Python 3.13 para este proyecto, ya que algunas dependencias podrían no ser compatibles todavía.

**2. Crear el entorno virtual**

```bash
py -3.13 -m venv .venv
```

**3. Activar el entorno virtual**

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate

# Git Bash
source .venv/Scripts/activate
```

**4. Actualizar las herramientas de instalación**

```bash
python -m pip install --upgrade pip setuptools wheel
```

**5. Instalar las librerías**

```bash
pip install -r requirements.txt
```

**6. Configurar las variables de entorno**

Copia el archivo de ejemplo y edítalo con tus datos locales:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

**Nota:** Asegúrate de tener el entorno virtual activado antes de instalar las dependencias y ejecutar el proyecto.

Variables disponibles:

| Variable        | Descripción                     | Ejemplo                                                    |
| --------------- | ------------------------------- | ---------------------------------------------------------- |
| `APP_NAME`      | Nombre de la aplicación         | `Panify API`                                               |
| `APP_ENV`       | Entorno de ejecución            | `development`                                              |
| `DEBUG`         | Modo depuración                 | `true`                                                     |
| `API_V1_PREFIX` | Prefijo de la versión de la API | `/api/v1`                                                  |
| `DATABASE_URL`  | Cadena de conexión a MySQL      | `mysql+pymysql://usuario:contrasena@localhost:3306/panify` |

> ⚠️ El archivo `.env` contiene datos privados y **nunca debe subirse al repositorio**. Si tu contraseña tiene caracteres especiales (`@`, `#`, `/`), debes codificarlos en la URL (por ejemplo, `@` se escribe `%40`).

**5. Ejecutar el proyecto**

```bash
uvicorn app.main:app --reload
```

**6. Verificar que todo funciona**

| Qué                                 | URL                                |
| ----------------------------------- | ---------------------------------- |
| El proyecto se ejecuta bajo la URL  | http://127.0.0.1:8000              |
| Documentación del backend (Swagger) | http://127.0.0.1:8000/docs         |
| Estado del servidor                 | http://127.0.0.1:8000/health       |
| Estado de la conexión con MySQL     | http://127.0.0.1:8000/health/ready |

Si `/health/ready` responde `{"status": "ready", "database": "connected"}`, el backend ya se comunica con MySQL. Si responde con error 503, revisa `DATABASE_URL` y que MySQL esté encendido.

### Pruebas

```bash
pytest
```

---

## 📁 Estructura del proyecto

```
Panify-Backend/
├── app/
│   ├── api/                    # Capa de entrada: rutas HTTP
│   │   ├── health.py           # Endpoints de estado (/health, /health/ready)
│   │   └── v1/
│   │       └── router.py       # Router principal de la versión 1 de la API
│   ├── core/                   # Configuración y utilidades centrales
│   │   ├── config.py           # Variables de entorno (Settings)
│   │   └── exceptions.py       # Excepciones personalizadas
│   ├── domain/                 # Reglas y conceptos del negocio
│   │   ├── entities/
│   │   ├── enums/              # ENUM del sistema (roles, estados, tipos)
│   │   └── interfaces/
│   ├── infrastructure/
│   │   └── database/
│   │       ├── base.py         # Clase Base de la que heredan los modelos
│   │       ├── connection.py   # Motor de conexión a MySQL
│   │       └── session.py      # Sesión de base de datos por petición
│   ├── models/                 # Modelos SQLAlchemy (tablas)
│   ├── repositories/           # Acceso a datos
│   ├── schemas/                # Esquemas Pydantic (entrada y salida de la API)
│   ├── services/               # Lógica de negocio
│   ├── utils/                  # Funciones de apoyo
│   └── main.py                 # Punto de entrada de la aplicación
├── scripts/                    # Scripts auxiliares
├── test/                       # Pruebas automatizadas
├── .env.example                # Plantilla de variables de entorno
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🌿 Flujo de trabajo en Git

### Ramas por módulo (Feature Branches)

```
feature/auth-login
feature/gestion-usuarios
feature/gestion-productos
feature/gestion-pedidos
feature/gestion-recibos
feature/gestion-entregas
```

### Commits semánticos

Formato: `<tipo>(<ámbito>): <descripción en imperativo y minúsculas, máx. 50 caracteres>`

- **Tipos:** `feat`, `fix`, `style`, `docs`, `refactor`, `chore`
- **Ámbitos comunes:** `ui`, `db`, `repo`, `cliente`, `admin`, `trimestre3`

Ejemplos:

```
docs(repo): actualizar readme del backend
feat(db): crear tablas de usuarios y roles
chore(repo): configurar gitignore
```

---

## 👥 Equipo

| Integrante                      | Módulo                   |
| ------------------------------- | ------------------------ |
| Brayan Sneyder Devia Muñoz      | Pedidos                  |
| Brandon Duvan Guevara Rodríguez | Recibos                  |
| Kevin Julián González Chavez    | Autenticación y Usuarios |
| Jeison Alejandro Diaz Acosta    | Entrega                  |
| Martin Cruz Muñoz               | Productos                |
