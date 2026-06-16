# FastAPI Basic Starter

Proyecto base mínimo con FastAPI.

## Requisitos

- Python 3.10 o superior

## Crear y activar el entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## Instalar dependencias

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configurar conexion a SQL Server

Copia `.env.example` a `.env` y completa las variables de conexion:

```bash
cp .env.example .env
```

La configuracion usa SQLAlchemy con `mssql+pyodbc` y el driver ODBC de SQL Server. El endpoint `/health/db` ejecuta `SELECT 1` para validar la conexion real.

La conexion a MongoDB usa `pymongo` y mantiene las bases usadas por `DataSacService`:

- `logs`
- `DataSac`
- `MayorAuxiliar`
- `AnalyticSac`

El endpoint `/health/mongo` ejecuta `ping` para validar la conexion real.

Al iniciar, la aplicacion valida la conexion y muestra en consola:

```text
Conexion con la base de datos establecida correctamente. Check=1
Conexion con MongoDB establecida correctamente. Check=1
```

Si alguna conexion falla, el servicio no arranca. Para desactivar temporalmente estas validaciones:

```env
CHECK_DATABASE_ON_STARTUP=false
CHECK_MONGO_ON_STARTUP=false
```

Variables CORS:

```env
APP_ENV=dev
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Cuando `APP_ENV=dev`, la API permite todos los origenes con `*`. En otros ambientes, `CORS_ALLOWED_ORIGINS` debe contener los origenes permitidos separados por comas.

Variables JWT para autenticacion:

```env
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=180
```

`JWT_SECRET_KEY` debe definirse con una clave larga y privada en cada ambiente.

## Ejecutar en desarrollo

```bash
fastapi dev
```

La API queda disponible en:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

Healthchecks:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/health/db
- http://127.0.0.1:8000/health/mongo

Auth:

- `POST /auth/login`: valida credenciales contra SQL Server y emite JWT.
- `GET /auth/menu/data-sac-web`: valida el token Bearer y devuelve el menu permitido para los roles del usuario.

La respuesta de `POST /auth/login` no incluye el campo `menu`. El menu se obtiene por separado desde `GET /auth/menu/data-sac-web`, usando `MenuPermisosDataSAC` en MongoDB y cruzando los roles SQL del usuario con `rolesPermitidosCodigos`.

## Ejecutar pruebas

```bash
pytest
```

## Estructura

```text
.
├── app
│   ├── __init__.py
│   ├── core
│   │   └── settings.py
│   ├── db
│   │   ├── base.py
│   │   ├── mongo.py
│   │   └── session.py
│   ├── main.py
│   ├── models
│   │   └── ...
│   ├── modules
│   │   └── auth
│   │       ├── repositories
│   │       ├── dependencies.py
│   │       ├── router.py
│   │       ├── schemas.py
│   │       ├── security.py
│   │       └── service.py
│   ├── repositories
│   │   ├── mongo
│   │   └── sql
│   └── routers
│       ├── __init__.py
│       └── health.py
├── tests
│   └── test_main.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Modelos

`app/models` contiene los modelos de persistencia SQLAlchemy migrados desde `DataSacService`, organizados por dominio. Los modelos importan `Base` o `BaseSecundaria` desde `app.db.base`; no deben abrir conexiones ni contener reglas de negocio.

Las consultas deben vivir en `app/repositories/sql` o `app/repositories/mongo`, y la logica de negocio debe construirse encima en servicios.

Para modulos nuevos de negocio, preferir la organizacion por modulo en `app/modules/<modulo>`:

- `router.py`: solo dependencias, request/response y delegacion al service.
- `service.py`: reglas de negocio, validaciones y transacciones.
- `repositories/`: consultas SQL o Mongo sin reglas de negocio.
- `schemas.py`: entradas y salidas Pydantic.

Convenciones para nuevos modelos:

- No usar `relationship`; las relaciones se resuelven con `join()` explicitos en repositorios.
- Mantener `ForeignKey` cuando exista en la tabla.
- Declarar cada `Column(...)` en una sola linea.
- Mantener `__tablename__`, `__table_args__` y `primary_key=True`.
