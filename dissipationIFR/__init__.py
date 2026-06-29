# dissipationIFR/__init__.py

__version__ = "0.0.0"
__author__ = "Till Moritz"

# Lazily expose submodules to avoid importing heavy optional dependencies on `import dissipationIFR`.
from importlib import import_module as _import_module

__all__ = ["plots", "tools", "utilities", "interactive", "__version__", "__author__"]

def __getattr__(name: str):
    if name in {"plots", "tools", "utilities", "interactive"}:
        module = _import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")