from pathlib import Path

# Expose the path to this config directory — useful for loading .yml and .mplstyle files
CONFIG_DIR = Path(__file__).parent
# Expose the path to the root of the dissipationIFR package — useful for loading data files
PACKAGE_DIR = CONFIG_DIR.parent
from dissipationIFR.config.variables import *