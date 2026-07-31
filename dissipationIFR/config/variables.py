import cmocean.cm as cmo
import numpy as np

Glider_variables = {
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


vars_to_keep = ['GLIDER_VERT_VELO_MODEL',
                'THETA',
                'TEMP',
                'GLIDE_SPEED',
                'SIGTHETA',
                'SIGMA_T',
                'PSAL',
                'PRES',
                'GLIDER_HORZ_VELO_MODEL',
                'GLIDE_ANGLE',
                'VBD_CC',
                'ROLL',
                'PITCH',
                'HEADING',
                'CNDC',
                'BUOYANCY',
                'DIVE_NUMBER',
                'PROFILE_NUMBER',
                'PHASE',
                'SENSOR_FLUOROMETER_0000',
                'SENSOR_CTD_245201',
                'SENSOR_OXYGEN_005',
                'VBD_MIN_CNTS',
                'VBD_CNTS_PER_CC',
                'VBD_CC_PER_CNTS',
                'MASS',
                'VOLMAX',
                'C_VBD',
                'HD_A',
                'HD_B',
                'HD_C',
                'PLATFORM_SERIAL_NUMBER',
                'PLATFORM_MODEL',
                'WMO_IDENTIFIER',
                'TRAJECTORY',
                'DEPLOYMENT_LATITUDE',
                'DEPLOYMENT_LONGITUDE',
                'DEPLOYMENT_TIME']


VMP_variables =  {
            'TIME': {
                'source': 'date',
                'dims': 'TIME',
                'name': 'TIME',
                'convert_time': True
            },
            'LONGITUDE': {
                'source': 'LON',
                'dims': 'TIME',
                'name': 'LONGITUDE',
                'attrs': {'units': 'degrees_east'}
            },
            'LATITUDE': {
                'source': 'LAT',
                'dims': 'TIME',
                'name': 'LATITUDE',
                'attrs': {'units': 'degrees_north'}
            },
            'PROFILE_NUMBER': {
                'source': 'casts',
                'dims': 'TIME',
                'name': 'PROFILE_NUMBER'
            },
            'ECHODEPTH': {
                'source': 'EchoDepth',
                'dims': 'TIME',
                'name': 'ECHODEPTH',
                'attrs': {'units': 'meters'}
            },
            'STATION_NAME': {
                'source': 'stname',
                'dims': 'TIME',
                'name': 'STATION_NAME',
                'handle_list': True
            },
            'EPSILON': {
                'source': 'eps',
                'dims': ['N_MEAS', 'TIME'],
                'name': 'EPSILON',
                'attrs': {'units': 'W/kg'}
            },
            'E1': {
                'source': 'e1',
                'dims': ['N_MEAS', 'TIME'],
                'name': 'E1'
            },
            'E2': {
                'source': 'e2',
                'dims': ['N_MEAS', 'TIME'],
                'name': 'E2'
            },
            'SIGTHETA': {
                'source': 'SIGTH',
                'dims': ['N_MEAS', 'TIME'],
                'name': 'SIGTHETA',
                'attrs': {'units': 'kg/m^3'}
            },
            'TEMP': {
                'source': 'T',
                'dims': ['N_MEAS', 'TIME'],
                'name': 'TEMP',
                'attrs': {'units': '°C'}
            },
            'DEPTH': {
                'source': 'z',
                'dims': ['N_MEAS', 'TIME'],
                'name': 'DEPTH',
                'attrs': {'units': 'meters'}
            },
            'PRES': {
                'source': 'P',
                'dims': ['N_MEAS', 'TIME'],
                'name': 'PRES',
                'attrs': {'units': 'dbar'}
            },
            'HAB': {
                'source': 'hab',
                'dims': ['N_MEAS', 'TIME'],
                'name': 'HAB',
                'attrs': {'units': 'm', 'long_name': 'Height above bottom'}
            }
        }