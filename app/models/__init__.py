import importlib
import pkgutil


def import_all_models() -> None:
    for module_info in pkgutil.walk_packages(__path__, prefix=f"{__name__}."):
        importlib.import_module(module_info.name)
