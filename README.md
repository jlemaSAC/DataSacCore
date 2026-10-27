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
El valor `APP_NAME` se envia como nombre de aplicacion en las conexiones ODBC, para identificar la API en los registros y sesiones de SQL Server (`DataSacCore` por defecto).

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
fastapi dev --port 9100
```

La API queda disponible en:

- http://127.0.0.1:9100
- http://127.0.0.1:9100/docs
- http://127.0.0.1:9100/redoc

Healthchecks:

- http://127.0.0.1:9100/health
- http://127.0.0.1:9100/health/db
- http://127.0.0.1:9100/health/mongo

Auth:

- `POST /auth/login`: login compartido que conserva el contrato usado por AnalyticSac.
- `POST /data-sac-web/auth/login`: login exclusivo de DataSacWeb; valida credenciales contra SQL Server y emite JWT.
- `GET /data-sac-web/auth/menu`: valida el token Bearer y devuelve el menu permitido para los roles del usuario.
- `GET /data-sac-web/auth/menu/completo`: devuelve el arbol completo del menu DataSacWeb, incluidos los items inactivos y roles asignados; requiere el rol administrador `001`.
- `GET /data-sac-web/auth/menu/{id_menu}`, `POST /data-sac-web/auth/menu`, `PATCH /data-sac-web/auth/menu/{id_menu}` y `DELETE /data-sac-web/auth/menu/{id_menu}`: administración de permisos de DataSacWeb; requieren el rol administrador `001`.

La respuesta de `POST /data-sac-web/auth/login` no incluye el campo `menu`. El menu se obtiene por separado desde `GET /data-sac-web/auth/menu`, usando la base MongoDB `DataSacWebAppMenu`: cruza los roles SQL del usuario con las asignaciones activas y construye el arbol del estado de menús vigente.

## Ejecutar pruebas

```bash
pytest
```

## Desplegar con Docker

La imagen usa la imagen oficial de Python, instala el driver oficial `msodbcsql18` requerido por `pyodbc` para SQL Server y ejecuta FastAPI con:

```bash
fastapi run app/main.py --host 0.0.0.0 --port 9100
```

Construir la imagen:

```bash
docker build -t datasac-core:latest .
```

Ejecutar con las variables de entorno del archivo `.env`:

```bash
docker run --rm --env-file .env -p 9100:9100 datasac-core:latest
```

O usando Compose:

```bash
docker compose up -d --build
```

La API quedara disponible en:

- http://127.0.0.1:9100
- http://127.0.0.1:9100/docs
- http://127.0.0.1:9100/health

Notas para produccion:

- No copiar `.env` dentro de la imagen; pasar secretos como variables de entorno, secret manager o variables del orquestador.
- Usar `APP_ENV=production` y definir `CORS_ALLOWED_ORIGINS` con los dominios reales del frontend.
- Mantener `CHECK_DATABASE_ON_STARTUP=true` y `CHECK_MONGO_ON_STARTUP=true` si se quiere impedir que la API arranque sin SQL Server o MongoDB.
- Publicar solo el puerto interno `9100` detras de un proxy/reverse proxy o balanceador con TLS.

## Publicacion de la imagen

El workflow `.github/workflows/docker-publish.yml` se ejecuta en cada pull
request y push dirigido a `main`:

1. Ejecuta las pruebas automatizadas.
2. Construye la imagen Docker.
3. En un push a `main`, publica la imagen en GitHub Container Registry.

Imagenes generadas:

```text
ghcr.io/jlemasac/datasaccore:latest
ghcr.io/jlemasac/datasaccore:sha-<commit>
```

La etiqueta SHA es la recomendada para despliegues reproducibles y rollback.

## Despliegue en servidor

Si el paquete GHCR es privado, iniciar sesion con un token que tenga unicamente
el permiso `read:packages`:

```bash
docker login ghcr.io -u USUARIO_GITHUB
```

Crear, por ejemplo, `/opt/datasac-core/compose.yaml`:

```yaml
services:
  api:
    image: ghcr.io/jlemasac/datasaccore:latest
    env_file:
      - .env
    environment:
      APP_ENV: production
    ports:
      - "9100:9100"
    restart: unless-stopped
```

El archivo `/opt/datasac-core/.env` debe crearse directamente en el servidor.
Luego iniciar el servicio:

```bash
cd /opt/datasac-core
docker compose pull
docker compose up -d
docker compose logs -f api
```

Validar el despliegue:

```bash
curl http://localhost:9100/health
```

Para actualizar a una imagen nueva:

```bash
docker compose pull
docker compose up -d
```

Para fijar o restaurar una version, reemplazar `latest` en `compose.yaml` por
la etiqueta correspondiente:

```text
ghcr.io/jlemasac/datasaccore:sha-<commit>
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


## Gestión de menús y permisos de DataSacWeb

La administración conserva los menús y las asignaciones previamente existentes en
la base Mongo configurada para DataSacWeb. Los cargos que
intervienen en autorización son los roles de `SEGURIDAD.ROL`; los identificadores
numéricos de `NOMINA.CARGO` no se convierten en códigos de rol.

- `/dashboard/seguridad/menus`: estructura, edición y configuración del menú.
- `/dashboard/seguridad/permisos/permisos-por-cargo`: perspectiva predeterminada.
- `/dashboard/seguridad/permisos/permisos-por-menu`: las mismas asignaciones por menú.
- `GET /seguridad/permisos`: árbol completo, cargos y versión del estado.
- `PATCH /seguridad/permisos`: diferencias explícitas y versión original.

Los endpoints requieren Bearer y verifican en SQL que el usuario siga habilitado
y tenga el rol administrativo existente `001`. No se crean roles ni permisos
administrativos adicionales. Los enlaces de las dos herramientas se añaden al
menú de ese administrador sin modificar los documentos de navegación existentes.

Ejemplo de lote (el identificador y la versión se obtienen del GET):

```json
{
  "version": "<sha256 devuelto por GET>",
  "cambios": [
    { "menu_id": "<id del menú>", "rol_codigo": "036", "conceder": true }
  ]
}
```

El servidor rechaza relaciones repetidas, cargos inexistentes y concesiones a
cargos inactivos. Los padres reciben acceso efectivo desde sus hijos sin conceder
acceso a hermanos ni a menús futuros. El permiso propio del padre se conserva por
separado. Las asignaciones históricas sin marca de acceso directo se conservan
al editar; no se ejecuta una migración destructiva al consultar.

### Guardado atómico con MongoDB independiente

La API puede funcionar con la instancia MongoDB independiente existente. No
requiere replica set: guarda el estado completo de menús, permisos y relaciones
en el documento `menu_estado` con `_id: "actual"`. La creación y las ediciones
usan una única escritura atómica, con una revisión que impide sobrescribir cambios
concurrentes. MongoDB limita el tamaño de un documento BSON a 16 MiB; la API
rechaza el guardado antes de llegar a 15 MiB para dejar margen.

Antes del primer cambio, la API lee `menu`, `permisos` y `rol_permisos` sin
modificarlos. El primer guardado copia su estado completo al nuevo documento y
aplica la operación en la misma escritura. En adelante `menu_estado/actual` es
la fuente de verdad para la navegación, la administración de menús y ambas vistas
de permisos. Los identificadores, códigos y asignaciones se conservan. Las tres
colecciones originales permanecen como respaldo de la migración y ya no reflejan
cambios posteriores; no deben usarse como fuente de permisos ni modificarse.

Para el cambio de versión, detener las escrituras administrativas y actualizar
todas las instancias de DataSacCore y cualquier consumidor externo que lea o
escriba esas tres colecciones. La aplicación anterior continuaría leyendo datos
antiguos después de la migración, incluso si se revoca un acceso. Tras actualizar
todos los consumidores, reiniciar la API y comprobar un lote en ambas vistas.
La API comprueba la huella de las colecciones originales y devuelve `503` si
detecta que otro proceso las modificó; resolver la divergencia antes de continuar.
Las colecciones originales no constituyen un respaldo actualizado para revertir
la aplicación después de guardar cambios en el nuevo documento: cualquier vuelta
atrás debe reconciliar primero el estado vigente.

La copia inicial exige que las colecciones originales permanezcan sin escrituras
durante el cambio de versión. MongoDB no ofrece una lectura y creación atómica de
varias colecciones en una instancia independiente, por lo que esta condición debe
coordinarse con los demás procesos. No activar el nuevo documento mientras una
versión anterior de la API siga sirviendo tráfico.

Una versión desactualizada devuelve `409` antes de cambiar asignaciones. El
frontend conserva el borrador y su resumen para revisar, descartar y recargar.
Después de guardar, ambas perspectivas reciben el mismo estado confirmado y se
refresca la navegación de la sesión del administrador. Las sesiones de otros
usuarios reciben el nuevo menú en su siguiente actualización; sus tokens no se
reescriben.

Validación específica:

```bash
.venv/bin/python -m pytest tests/test_auth.py tests/test_seguridad_permisos.py tests/test_permisos_mongo_independiente.py tests/test_seguridad_roles.py
```

Las pruebas incluyen fallos antes de publicar, conflictos de versión, preservación
de accesos históricos, autorización y ambas perspectivas. El guardado se puede
validar en una base de prueba aislada de la misma instancia independiente.
