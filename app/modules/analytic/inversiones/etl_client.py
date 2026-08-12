import json
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class EtlReporteInversionesError(RuntimeError):
    pass


class EtlReporteInversionesClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def cargar_mes(self, fecha_fin_mes: date) -> dict[str, Any]:
        parametros = urlencode(
            {
                "fecha_desde": fecha_fin_mes.isoformat(),
                "fecha_hasta": fecha_fin_mes.isoformat(),
            }
        )
        request = Request(
            f"{self.base_url}/mongo/reporte-analitico-inversiones?{parametros}",
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detalle = exc.read().decode("utf-8", errors="replace")
            raise EtlReporteInversionesError(
                f"El ETL respondió HTTP {exc.code}: {detalle}"
            ) from exc
        except URLError as exc:
            raise EtlReporteInversionesError(f"No se pudo conectar al ETL: {exc.reason}") from exc
