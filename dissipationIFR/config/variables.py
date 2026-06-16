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
    'SIGMA_T': {'attributes': {
        'long_name': 'Potential Density Anomaly',
        'units': 'kg/m³',
        },
        'colormap': cmo.dense,
    },
}