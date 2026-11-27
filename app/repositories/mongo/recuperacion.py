from typing import Any


TIPOS_TRANSACCION_EXCLUIDOS = (
    "CASTIGO DE PRÉSTAMO",
    "CONDONACION DE INTERES MORA",
)


def filtro_transacciones_recuperacion() -> dict[str, Any]:
    """Filtra el tipo de transacción usando el campo actual o su alias histórico."""
    return {
        "$expr": {
            "$not": [
                {
                    "$in": [
                        {"$ifNull": ["$TIPO_TRANSACCION", "$TipoTransaccion"]},
                        list(TIPOS_TRANSACCION_EXCLUIDOS),
                    ]
                }
            ]
        }
    }
