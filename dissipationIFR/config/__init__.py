from pathlib import Path

from .variables import variables, vars_to_keep

CONFIG_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CONFIG_DIR.parent

__all__ = ["CONFIG_DIR", "PACKAGE_DIR", "variables", "vars_to_keep"]