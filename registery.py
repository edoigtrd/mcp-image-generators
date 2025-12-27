from imagen.abstract import ImageGenerator
from typing import Dict, Type


REGISTERED_GENERATORS : dict[str, type[ImageGenerator]] = {}

def register(cls : type[ImageGenerator]) -> type[ImageGenerator]:
    REGISTERED_GENERATORS[cls.__name__] = cls
    return cls

def register_generator(name: str):
    def decorator(cls: Type[ImageGenerator]) -> Type[ImageGenerator]:
        REGISTERED_GENERATORS[name] = cls
        return cls

    return decorator

# Dynamically import all modules in this package to register rerankers
import importlib
import pkgutil
from pathlib import Path

modules_path = Path(__file__).parent / "imagen"

for module_info in pkgutil.iter_modules([str(modules_path)]):
    module_name = module_info.name
    importlib.import_module(f"imagen.{module_name}")