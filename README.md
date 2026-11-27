# Panify — Backend

> **"Horneamos Calidad, Entregamos Confianza y Unimos Lazos."**

Backend de **Panify**, el sistema de gestión de pedidos, inventario, recibos y entregas de **Distribuciones Oro Pan**, una fábrica de pan. Centraliza la lógica de negocio y el acceso a los datos de la plataforma web, reemplazando el registro manual de pedidos (llamadas y papel).

> 🚧 **Estado del proyecto:** en desarrollo. El backend ya cuenta con endpoints para autenticación, usuarios, inventario, pedidos y recibos. La documentación interactiva permite consultar las rutas disponibles cuando el servidor está activo: `http://127.0.0.1:8000/docs`.

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
- **Valores derivados:** subtotal y estado de stock. El total del recibo se calcula con precios congelados y se persiste al emitirlo.

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

**Pendiente por definir:** estrategia de despliegue.

## 🔌 API y endpoints actuales

La API principal usa el prefijo `/api/v1`; los endpoints de salud no tienen ese prefijo. Las rutas protegidas requieren el encabezado `Authorization: Bearer <token>`, que se obtiene al iniciar sesión. Puedes consultar los esquemas de entrada y salida y probar las rutas en Swagger: `http://127.0.0.1:8000/docs`.

### Salud

| Método | Endpoint | Acceso | Función |
| --- | --- | --- | --- |
| `GET` | `/health` | Público | Comprueba que el servidor está activo. |
| `GET` | `/health/ready` | Público | Comprueba la conexión a MySQL; devuelve `503` si la base no está disponible. |

### Autenticación y recuperación de contraseña

| Método | Endpoint | Acceso | Función |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Público | Valida correo y contraseña y devuelve un JWT. |
| `GET` | `/api/v1/auth/me` | JWT | Devuelve el perfil del usuario autenticado. |
| `POST` | `/api/v1/auth/logout` | JWT | Revoca el token actual. |
| `POST` | `/api/v1/auth/forgot-password` | Público | Solicita por correo un código de recuperación. |
| `POST` | `/api/v1/auth/reset-password` | Público | Valida el código y establece una nueva contraseña. |

### Usuarios

| Método | Endpoint | Acceso | Función |
| --- | --- | --- | --- |
| `POST` | `/api/v1/users/` | Público para clientes; personal requiere Administrador o Superadmin; crear Administrador requiere Superadmin | Registra un usuario según el rol solicitado. |
| `GET` | `/api/v1/users/` | Superadmin | Lista usuarios; admite `role`, `is_active`, `skip` y `limit`. |
| `GET` | `/api/v1/users/{user_id}` | Superadmin | Consulta un usuario por ID. |
| `PATCH` | `/api/v1/users/{user_id}` | Superadmin | Actualiza los datos permitidos del usuario. |
| `PATCH` | `/api/v1/users/{user_id}/status` | Superadmin | Activa o desactiva un usuario. |

### Inventario y productos

| Método | Endpoint | Acceso | Función |
| --- | --- | --- | --- |
| `POST` | `/api/v1/inventario/productos` | Administrador o Panadero | Crea un producto y su inventario inicial. |
| `PATCH` | `/api/v1/inventario/productos/{id_producto}` | Administrador o Panadero | Actualiza precio o existencias de un producto. |
| `GET` | `/api/v1/inventario/productos` | Público; JWT opcional | Lista productos; acepta `categoria` y `buscar`. Sin rol gestor, solo muestra productos activos. |
| `GET` | `/api/v1/inventario/productos/{id_producto}` | Público; JWT opcional | Consulta un producto; sin rol gestor, solo permite consultar productos activos. |
| `GET` | `/api/v1/inventario/productos/{id_producto}/disponibilidad?cantidad=1` | JWT | Comprueba si hay existencias para la cantidad solicitada. |
| `POST` | `/api/v1/inventario/movimientos/descuento` | Rol `Sistema` | Descuenta del inventario los productos asociados a un pedido. |
| `GET` | `/api/v1/inventario/alertas` | Administrador o Panadero | Lista productos con inventario bajo; acepta el parámetro opcional `umbral`. |
| `PATCH` | `/api/v1/inventario/productos/{id_producto}` | Administrador | Inactiva un producto. |

### Pedidos

| Método | Endpoint | Acceso | Función |
| --- | --- | --- | --- |
| `POST` | `/api/v1/orders` | Cliente, Administrador o Superadmin | Crea un pedido. |
| `GET` | `/api/v1/orders` | JWT | Lista pedidos visibles para el usuario; acepta `estadoPedido`, `filtroTexto`, `page` y `page_size`. |
| `GET` | `/api/v1/orders/dispatch-queue` | Panadero, Domiciliario o Administrador | Consulta la cola de pedidos para despacho. |
| `GET` | `/api/v1/orders/history/filter?fechaInicio=AAAA-MM-DD&fechaFin=AAAA-MM-DD` | JWT | Filtra el historial por fechas; acepta también `page` y `page_size`. |
| `GET` | `/api/v1/orders/{idPedido}` | JWT | Consulta el detalle de un pedido sujeto a los permisos del usuario. |
| `PATCH` | `/api/v1/orders/{idPedido}/cancel` | Cliente propietario del pedido o Administrador | Cancela un pedido cuando las reglas de negocio lo permiten. |
| `PATCH` | `/api/v1/orders/{idPedido}/status` | Panadero, Domiciliario o Administrador | Actualiza el estado del pedido, sujeto a las reglas de negocio. |
| `POST` | `/api/v1/orders/{order_id}/confirm` | Panadero, Administrador o Superadmin | Confirma un pedido pendiente y genera su recibo. |

### Recibos

| Método | Endpoint | Acceso | Función |
| --- | --- | --- | --- |
| `GET` | `/api/v1/receipts/` | JWT | Lista recibos visibles; acepta `search`, `page` y `page_size`. |
| `GET` | `/api/v1/receipts/{receipt_id}` | JWT | Consulta el recibo, el pedido, el cliente y los productos con precios congelados. |
| `GET` | `/api/v1/receipts/{receipt_id}/pdf` | JWT | Descarga el recibo en PDF. |

En recibos, Cliente solo ve los propios; Domiciliario, los pedidos que tiene asignados; Administrador y Superadmin pueden consultar todos. Panadero puede confirmar pedidos, pero no consultar ni descargar recibos. `search` admite hasta 100 caracteres y `page`/`page_size` deben ser positivos. La fecha de emisión se asigna en el servidor.

---

## 🚀 Instalación y ejecución

Esta guía usa **Git Bash** como terminal principal. Desde la raíz del proyecto, sigue los pasos en orden. Se recomienda Python **3.13**; el proyecto requiere Python 3.12 o superior.

### 1. Clonar el repositorio

```bash
git clone https://github.com/Panify-HQ/Panify-Backend.git
cd Panify-Backend
```

### 2. Crear y activar el entorno virtual

En Windows con Git Bash y el lanzador de Python instalado:

```bash
py -3.13 -m venv .venv
source .venv/Scripts/activate
```

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Confirma que el entorno está activo y usa la versión esperada:

```bash
python --version
```

En la terminal activa debe aparecer `(.venv)`. Activa de nuevo el entorno cada vez que abras una terminal para trabajar en el proyecto.

### 3. Instalar dependencias

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Crear la base de datos MySQL

Inicia MySQL y crea una base vacía llamada `panify`. Puedes ejecutar este SQL desde MySQL Workbench (en una pestaña de consulta) o desde tu cliente SQL:

```sql
CREATE DATABASE panify
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 5. Configurar la conexión y las variables de entorno

Crea tu archivo local a partir de la plantilla:

```bash
cp .env.example .env
```

Abre `.env` y configura, como mínimo:

- `DATABASE_URL`: conexión que usa **la aplicación y Alembic** para acceder a MySQL. Sustituye el usuario y la contraseña por los de tu instalación:

  ```text
  DATABASE_URL=mysql+pymysql://usuario:clave@localhost:3306/panify
  ```

#### Autenticación (JWT)

Genera una clave secreta y copia el resultado en `.env` como valor de `JWT_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Por ejemplo, reemplaza el valor de ejemplo por `JWT_SECRET_KEY=<clave-generada>`. Esta clave es privada: no la compartas ni la subas a Git.

Si la contraseña de MySQL contiene caracteres especiales como `@`, `#` o `/`, codifícalos para que sean válidos en la URL (por ejemplo, `@` se escribe `%40`). Si usarás la recuperación de contraseña por correo, configura también `SMTP_USER` y `SMTP_PASSWORD` con credenciales SMTP válidas; para Gmail utiliza una contraseña de aplicación.

> **Seguridad:** `.env` contiene credenciales y secretos locales. No lo compartas ni lo subas al repositorio; Git lo ignora. Usa `.env.example` como plantilla, nunca como almacén de credenciales reales.

### 6. Crear las tablas con Alembic

Desde la raíz del repositorio y con el entorno virtual activo, ejecuta:

```bash
python -m alembic upgrade heads
```

Se usa `heads` (plural) porque las migraciones actuales tienen más de una rama. Este paso crea y actualiza las tablas, incluidos los roles iniciales necesarios para crear el SuperAdmin.

#### Datos de prueba (opcional)

El [script SQL de datos de prueba](https://github.com/Panify-HQ/Panify-Documentacion/blob/main/docs/04-base-de-datos-y-backend/Script_DDL_DML_MySQL.sql) inserta registros en las tablas existentes; no crea el esquema. Por eso, solo se considera después de aplicar las migraciones y sobre una base local desechable, nunca sobre producción.

**No lo ejecutes directamente todavía:** hay diferencias que deben corregirse en el script para que coincida con el esquema actual del backend:

- La columna de dirección del cliente se llama `direccion` en el backend; el script usa `dirección`.
- Los productos admiten `ACTIVO`, `INACTIVO` o `AGOTADO`; los pedidos admiten `Pendiente`, `En preparación`, `Listo`, `En camino`, `Entregado` o `Cancelado`. El script usa valores distintos para algunos de esos estados.
- `fechaHoraEntregaEstimada` es obligatoria en cada pedido y el script no la incluye en sus inserciones.
- Los hashes de contraseña de ejemplo están incompletos; esos usuarios no podrán iniciar sesión hasta que se sustituyan por hashes válidos.
- Aunque crea pedidos y detalles, el script no inserta filas en `recibos`; no bastará para probar los endpoints de recibos.

Antes de usarlo, adapta esos datos, confirma que la base seleccionada es `panify` y ejecútalo únicamente en un entorno de pruebas.

### 7. Crear el SuperAdmin

Ejecuta el script interactivo:

```bash
python -m scripts.create_super_admin
```

Ingresa nombre, apellido, correo, teléfono y contraseña cuando los solicite. La contraseña se guarda protegida. Si ya existe un SuperAdmin, el script no crea otro. Si informa que falta el rol, comprueba que las migraciones del paso anterior terminaron correctamente y que `.env` apunta a la base `panify` correcta.

### 8. Iniciar el backend

```bash
python -m uvicorn app.main:app --reload
```

Deja esa terminal abierta mientras uses la API. `--reload` es útil durante desarrollo; no se recomienda para producción.

### 9. Verificar que el backend y MySQL estén disponibles

Con el servidor en ejecución, abre otra terminal o navegador:

| Comprobación | URL | Resultado esperado |
| --- | --- | --- |
| Servidor activo | `http://127.0.0.1:8000/health` | `{"status":"ok","service":"panify-api"}` |
| Conexión a MySQL | `http://127.0.0.1:8000/health/ready` | `{"status":"ready","database":"connected"}` |
| Documentación interactiva (Swagger) | `http://127.0.0.1:8000/docs` | Documentación de los endpoints |

También puedes comprobar los health checks desde Git Bash:

```bash
curl http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/health/ready
```

La API versionada usa el prefijo `/api/v1`.

### Solución de problemas frecuentes

- **MySQL no disponible o respuesta 503 en `/health/ready`:** confirma que el servicio MySQL está iniciado, que la base `panify` existe y que `DATABASE_URL` tiene el usuario, contraseña, host y puerto correctos.
- **Error de tabla inexistente:** vuelve a ejecutar `python -m alembic upgrade heads` con el entorno virtual activo y revisa que Alembic use el mismo `.env` y la misma base que la aplicación.
- **No se envían correos de recuperación:** configura `SMTP_USER` y `SMTP_PASSWORD` en `.env`; en Gmail se requiere una contraseña de aplicación.
- **No se encuentra el comando `python`:** instala Python 3.12 o superior y verifica que esté disponible en la terminal.
- **No se encuentra `uvicorn` o `alembic`:** activa `.venv` y vuelve a instalar las dependencias con `python -m pip install -r requirements.txt`.

### Pruebas

```bash
python -m pytest
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
