# Prueba de despliegue antes del merge

## Objetivo

Validar que una rama candidata puede convertirse en una imagen Docker funcional
antes de integrarla en `main` y publicarla en GitHub Container Registry (GHCR).

Este procedimiento reproduce localmente las etapas principales de
`.github/workflows/docker-publish.yml`:

```text
pruebas Python -> build de la imagen -> arranque del contenedor -> healthchecks
```

La validacion debe ejecutarse desde la rama que se pretende integrar.

## Requisitos

- Python 3.12.
- Entorno virtual del proyecto.
- Docker Engine o Docker Desktop iniciado.
- Archivo `.env` local para las pruebas de integracion. Este archivo no debe
  agregarse al repositorio.

Confirmar la rama y que no existan cambios locales inesperados:

```bash
git branch --show-current
git status --short
```

## 1. Ejecutar las pruebas automatizadas

Activar el entorno e instalar las mismas dependencias usadas por GitHub Actions:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Resultado requerido:

```text
Todas las pruebas pasan y el comando termina con codigo 0.
```

Si una prueba falla, no se debe aprobar el merge. El job `docker` depende del
job `test`, por lo que GitHub Actions tampoco publicara una imagen en ese estado.

### Inconsistencia conocida al crear este documento

La documentacion funcional indica un limite de 24 meses, mientras que
`MAX_MESES_RANGO` esta configurado en 60. La regla de negocio debe definirse y
luego alinearse en el servicio, las pruebas y la documentacion antes de aprobar
el merge.

## 2. Construir la imagen candidata

Usar una etiqueta local que no se confunda con una imagen de produccion:

```bash
docker build --pull -t datasac-core:pre-merge .
```

Resultado requerido:

```text
El build termina sin errores y crea datasac-core:pre-merge.
```

Confirmar la imagen:

```bash
docker image inspect datasac-core:pre-merge
```

## 3. Prueba de arranque sin servicios externos

Esta prueba valida el empaquetado, el comando de inicio y el endpoint base. Las
comprobaciones de SQL Server y MongoDB se desactivan solamente para este smoke
test local.

```bash
docker run --rm -d \
  --name datasac-core-pre-merge \
  --env-file .env \
  -e CHECK_DATABASE_ON_STARTUP=false \
  -e CHECK_MONGO_ON_STARTUP=false \
  -p 9100:9100 \
  datasac-core:pre-merge
```

Revisar el estado y los logs:

```bash
docker ps --filter name=datasac-core-pre-merge
docker logs datasac-core-pre-merge
curl --fail --show-error http://127.0.0.1:9100/health
```

Resultado requerido:

- El contenedor permanece en ejecucion.
- Los logs no muestran errores de importacion o de configuracion.
- `/health` responde con HTTP 200.

Confirmar tambien el healthcheck definido en el `Dockerfile`:

```bash
docker inspect \
  --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}sin-healthcheck{{end}}' \
  datasac-core-pre-merge
```

El resultado esperado, despues del periodo inicial, es `healthy`.

## 4. Prueba de integracion con servicios reales

Esta etapa requiere que `.env` contenga credenciales de un ambiente de pruebas,
nunca credenciales de produccion. Ejecutar el contenedor sin sobrescribir las
validaciones de inicio:

```bash
docker stop datasac-core-pre-merge
docker run --rm -d \
  --name datasac-core-pre-merge \
  --env-file .env \
  -e APP_ENV=production \
  -e CHECK_DATABASE_ON_STARTUP=true \
  -e CHECK_MONGO_ON_STARTUP=true \
  -p 9100:9100 \
  datasac-core:pre-merge
```

Validar las dependencias:

```bash
curl --fail --show-error http://127.0.0.1:9100/health
curl --fail --show-error http://127.0.0.1:9100/health/db
curl --fail --show-error http://127.0.0.1:9100/health/db-secondary
curl --fail --show-error http://127.0.0.1:9100/health/mongo
```

Si la base secundaria no aplica al ambiente evaluado, registrar `No aplica` en
la evidencia en lugar de ocultar el resultado.

## 5. Validacion del pull request

Crear el pull request hacia `main` solamente despues de completar las pruebas
locales. En el pull request, el workflow debe mostrar:

```text
Run tests                  success
Build and publish image    success
```

En un pull request, el segundo job construye la imagen pero no la publica. La
publicacion en GHCR se realiza despues del push a `main`.

No aprobar el merge si un check esta fallando, cancelado o pendiente sin una
explicacion documentada.

## 6. Evidencia de prueba

Copiar esta tabla en la descripcion del pull request y completar los resultados:

| Validacion | Resultado | Evidencia u observacion |
| --- | --- | --- |
| Rama revisada | Pendiente | Nombre de la rama |
| Commit revisado | Pendiente | SHA del commit |
| Pruebas Python | Pendiente | Cantidad de pruebas aprobadas |
| Build Docker | Pendiente | Etiqueta local y hora |
| Arranque sin dependencias | Pendiente | Resultado de `/health` |
| Healthcheck Docker | Pendiente | `healthy` esperado |
| Conexion SQL principal | Pendiente | Resultado de `/health/db` |
| Conexion SQL secundaria | Pendiente | Resultado o `No aplica` |
| Conexion MongoDB | Pendiente | Resultado de `/health/mongo` |
| GitHub Actions del PR | Pendiente | Enlace a la ejecucion |
| Aprobacion para merge | Pendiente | Responsable y fecha |

Estados permitidos:

```text
Aprobado | Fallido | No aplica
```

## 7. Limpieza local

Detener el contenedor al finalizar:

```bash
docker stop datasac-core-pre-merge
```

Eliminar la imagen candidata cuando ya no sea necesaria:

```bash
docker image rm datasac-core:pre-merge
```

## Criterio final para autorizar el merge

El merge esta listo cuando:

- Todas las pruebas automatizadas pasan.
- La imagen se construye desde cero sin errores.
- El contenedor inicia y queda `healthy`.
- Los healthchecks requeridos responden correctamente en el ambiente de prueba.
- Los dos jobs del pull request terminan en `success`.
- La evidencia queda registrada en el pull request.
