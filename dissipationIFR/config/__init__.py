from pathlib import Path

from .variables import Glider_variables, vars_to_keep, VMP_variables

CONFIG_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CONFIG_DIR.parent

__all__ = ["CONFIG_DIR", "PACKAGE_DIR", "Glider_variables", "vars_to_keep", "VMP_variables"]