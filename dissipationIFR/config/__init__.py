from pathlib import Path

from .variables import Glider_variables, vars_to_keep, VMP_variables

CONFIG_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CONFIG_DIR.parent

plotting_style = CONFIG_DIR / "plotting.mplstyle"

__all__ = ["CONFIG_DIR", "PACKAGE_DIR", "plotting_style", "Glider_variables", "vars_to_keep", "VMP_variables",]