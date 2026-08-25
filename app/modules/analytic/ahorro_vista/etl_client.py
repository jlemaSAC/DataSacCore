import json
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class EtlReporteAhorroVistaError(RuntimeError):
    pass


class EtlReporteAhorroVistaClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def cargar_mes(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        es_programado: bool | None = None,
    ) -> dict[str, Any]:
        parametros_carga: dict[str, str | bool] = {
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
        }
        if es_programado is not None:
            parametros_carga["es_programado"] = es_programado
        parametros = urlencode(parametros_carga)
        request = Request(
            f"{self.base_url}/mongo/reporte-analitico-ahorros-vista?{parametros}",
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detalle = exc.read().decode("utf-8", errors="replace")
            raise EtlReporteAhorroVistaError(
                f"El ETL respondió HTTP {exc.code}: {detalle}"
            ) from exc
        except URLError as exc:
            raise EtlReporteAhorroVistaError(f"No se pudo conectar al ETL: {exc.reason}") from exc
