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

## Ejecutar en desarrollo

```bash
fastapi dev
```

La API queda disponible en:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

## Ejecutar pruebas

```bash
pytest
```

## Estructura

```text
.
├── app
│   ├── __init__.py
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

