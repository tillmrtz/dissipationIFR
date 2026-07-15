import cmocean.cm as cmo
import numpy as np

variables = {
    'EPSILON': {'attributes': {
        'long_name': 'Dissipation Rate of Turbulent Kinetic Energy',
        'units': 'W/kg',
        },
        'colormap': cmo.delta,
    },
    'TEMP': {'attributes': {
        'long_name': 'Temperature',
        'units': '°C',
        },
        'colormap': cmo.thermal,
    },
    'PSAL': {'attributes': {
        'long_name': 'Salinity',
        'units': 'PSU',
        },
        'colormap': cmo.haline,
    },
    'DENSITY': {'attributes': {
        'long_name': 'Density',
        'units': 'kg/m³',
        },
        'colormap': cmo.dense,
    },
    'W_MEAS': {'attributes': {
        'long_name': 'Measured Vertical Velocity',
        'units': 'cm/s',
        },
        'colormap': cmo.speed,
    },
    'W_WATER': {'attributes': {
        'long_name': 'Vertical Velocity of Water',
        'units': 'cm/s',
        },
        'colormap': cmo.speed,
    },
    'N': {'attributes': {
        'long_name': 'Brunt-Väisälä Frequency',
        'units': '1/s',
        },
        'colormap': cmo.thermal,
    },
    'N_SORTED': {'attributes': {
        'long_name': 'Sorted Brunt-Väisälä Frequency',
        'units': '1/s',
        },
        'colormap': cmo.thermal,
    },
    'SIGMA_T': {'attributes': {
        'long_name': 'Potential Density Anomaly',
        'units': 'kg/m³',
        },
        'colormap': cmo.dense,
    },
}