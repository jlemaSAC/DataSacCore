from decimal import Decimal, InvalidOperation
from typing import Any


TRUE_VALUES = {"1", "TRUE", "T", "SI", "S", "YES", "Y", "DIFERIDO"}
FALSE_VALUES = {"0", "FALSE", "F", "NO", "N", "NONE", "NULL", ""}


def normalizar_texto(value: Any, default: str = "") -> str:
    if value is None:
        return default

    text = str(value).strip()
    if not text:
        return default

    return " ".join(text.upper().split())


def normalizar_numero_prestamo(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return normalizar_texto(value)


def normalizar_codigo_usuario(value: Any) -> str:
    return normalizar_texto(value)


def _normalizar_decimal_text(value: Any) -> str:
    text = str(value).strip()
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            return text.replace(".", "").replace(",", ".")
        return text.replace(",", "")
    if "," in text:
        return text.replace(",", ".")
    return text


def to_float_safe(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default

    if isinstance(value, (int, float, Decimal)):
        return float(value)

    text = _normalizar_decimal_text(value)
    if not text:
        return default

    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return default


def to_int_safe(value: Any, default: int | None = 0) -> int | None:
    if value is None or isinstance(value, bool):
        return default

    if isinstance(value, int):
        return value

    numeric_value = to_float_safe(value, default=0.0)
    try:
        return int(numeric_value)
    except (TypeError, ValueError):
        return default


def es_diferido(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float, Decimal)):
        return value != 0

    normalized = normalizar_texto(value)
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False

    return False


def normalizar_estado_prestamo(value: Any) -> str:
    return normalizar_texto(value)


def normalizar_calificacion(value: Any) -> str:
    return normalizar_texto(value)

