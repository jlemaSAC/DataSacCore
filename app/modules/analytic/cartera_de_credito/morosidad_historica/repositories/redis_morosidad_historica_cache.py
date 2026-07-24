import json
import logging
from collections.abc import Iterable

from redis import Redis
from redis.exceptions import RedisError

from app.modules.analytic.cartera_de_credito.morosidad_historica.schemas import (
    MorosidadHistoricaAgrupacion,
)


logger = logging.getLogger("uvicorn.error")


class RedisMorosidadHistoricaCacheUnavailable(RuntimeError):
    """La operacion administrativa no se puede completar sin Redis."""


class RedisMorosidadHistoricaCache:
    """Cachea por mes cerrado la respuesta ya normalizada para el contrato HTTP."""

    key_prefix = "cartera:morosidad-historica:v1"

    def __init__(self, client: Redis | None) -> None:
        self.client = client

    def obtener_meses(
        self, periodos: Iterable[str]
    ) -> dict[str, list[MorosidadHistoricaAgrupacion]]:
        if self.client is None:
            return {}

        periodos_unicos = list(dict.fromkeys(periodos))
        if not periodos_unicos:
            return {}

        try:
            valores = self.client.mget([self._key(periodo) for periodo in periodos_unicos])
        except RedisError:
            logger.warning("No fue posible leer cache Redis de morosidad historica", exc_info=True)
            return {}

        resultado: dict[str, list[MorosidadHistoricaAgrupacion]] = {}
        for periodo, valor in zip(periodos_unicos, valores, strict=True): # type: ignore
            if valor is None:
                continue
            try:
                contenido = json.loads(valor)
                resultado[periodo] = [
                    MorosidadHistoricaAgrupacion.model_validate(item)
                    for item in contenido["agrupaciones"]
                ]
            except (KeyError, TypeError, ValueError):
                logger.warning(
                    "Entrada invalida de cache Redis para morosidad historica. periodo=%s",
                    periodo,
                    exc_info=True,
                )
        return resultado

    def guardar_mes(
        self, periodo: str,
        agrupaciones: list[MorosidadHistoricaAgrupacion],
    ) -> None:
        if self.client is None:
            return

        valor = json.dumps(
            {"agrupaciones": [item.model_dump(mode="json") for item in agrupaciones]},
            separators=(",", ":"),
        )
        try:
            self.client.set(self._key(periodo), valor)
        except RedisError:
            logger.warning(
                "No fue posible guardar cache Redis de morosidad historica. periodo=%s",
                periodo,
                exc_info=True,
            )

    def limpiar_cache(self) -> int:
        """Elimina solo las claves de esta cache, sin bloquear Redis con KEYS."""
        if self.client is None:
            raise RedisMorosidadHistoricaCacheUnavailable(
                "Redis no esta configurado para la cache de morosidad historica."
            )

        eliminadas = 0
        claves_lote: list[str] = []
        try:
            for clave in self.client.scan_iter(match=f"{self.key_prefix}:*", count=500):
                claves_lote.append(clave)
                if len(claves_lote) == 500:
                    eliminadas += self.client.unlink(*claves_lote) # type: ignore
                    claves_lote.clear()
            if claves_lote:
                eliminadas += self.client.unlink(*claves_lote) # type: ignore
            return eliminadas
        except RedisError as exc:
            logger.warning("No fue posible limpiar cache Redis de morosidad historica", exc_info=True)
            raise RedisMorosidadHistoricaCacheUnavailable(
                "No fue posible conectar con Redis para limpiar la cache."
            ) from exc

    @classmethod
    def _key(cls, periodo: str) -> str:
        return f"{cls.key_prefix}:{periodo}"
