import hashlib
import json
import logging
from collections.abc import Iterable
from dataclasses import asdict
from datetime import date

from redis import Redis
from redis.exceptions import RedisError

from app.modules.analytic.cartera_de_credito.comparativo_cartera.domain import (
    TotalesCartera,
)


logger = logging.getLogger("uvicorn.error")


class RedisComparativoCarteraCache:
    key_prefix = "cartera:comparativo:v1"
    ttl_seconds = 21600

    def __init__(self, client: Redis | None) -> None:
        self.client = client

    def obtener(
        self,
        fechas: Iterable[date],
        agencias: list[str],
        filtrar_diferidos: bool | None,
    ) -> dict[date, TotalesCartera]:
        if self.client is None:
            return {}

        fechas_unicas = sorted(set(fechas))
        if not fechas_unicas:
            return {}
        scope = self._scope(agencias, filtrar_diferidos)
        try:
            valores = self.client.mget(
                [self._key(fecha, scope) for fecha in fechas_unicas]
            )
        except RedisError:
            logger.warning("No fue posible leer cache del comparativo de cartera", exc_info=True)
            return {}

        resultado: dict[date, TotalesCartera] = {}
        for fecha, valor in zip(fechas_unicas, valores, strict=True):
            if valor is None:
                continue
            try:
                data = json.loads(valor)
                data["fecha_corte"] = date.fromisoformat(data["fecha_corte"])
                resultado[fecha] = TotalesCartera(**data)
            except (KeyError, TypeError, ValueError):
                logger.warning(
                    "Entrada invalida de cache del comparativo. fecha=%s",
                    fecha,
                    exc_info=True,
                )
        return resultado

    def guardar(
        self,
        totales: Iterable[TotalesCartera],
        agencias: list[str],
        filtrar_diferidos: bool | None,
    ) -> None:
        if self.client is None:
            return

        items = list(totales)
        if not items:
            return
        scope = self._scope(agencias, filtrar_diferidos)
        try:
            pipeline = self.client.pipeline(transaction=False)
            for item in items:
                payload = asdict(item)
                payload["fecha_corte"] = item.fecha_corte.isoformat()
                pipeline.setex(
                    self._key(item.fecha_corte, scope),
                    self.ttl_seconds,
                    json.dumps(payload, separators=(",", ":")),
                )
            pipeline.execute()
        except RedisError:
            logger.warning("No fue posible guardar cache del comparativo de cartera", exc_info=True)

    @staticmethod
    def _scope(agencias: list[str], filtrar_diferidos: bool | None) -> str:
        contenido = json.dumps(
            {
                "agencias": sorted(agencias),
                "filtrar_diferidos": filtrar_diferidos,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def _key(cls, fecha: date, scope: str) -> str:
        return f"{cls.key_prefix}:{scope}:{fecha:%Y%m%d}"
