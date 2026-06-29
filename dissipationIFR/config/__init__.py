from pathlib import Path

from .variables import variables

CONFIG_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CONFIG_DIR.parent
glider_yml = CONFIG_DIR / "glider_data.yml"

__all__ = ["CONFIG_DIR", "PACKAGE_DIR", "glider_yml", "variables"]