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
│   │   └── session.py
│   ├── main.py
│   └── routers
│       ├── __init__.py
│       └── health.py
├── tests
│   └── test_main.py
├── pyproject.toml
├── requirements.txt
└── README.md
```
