import xarray as xr
import numpy as np


def calc_vertical_velocity(time: np.ndarray, depth: np.ndarray) -> np.ndarray:
    """
    Compute the vertical velocity of the glider from the pressure rate.

    Parameters
    ----------
    time : np.ndarray
        Array of times.
    depth : np.ndarray
        Array of depths.

    Returns
    -------
    w_meas : np.ndarray
        Array of measured vertical velocities.
    """
    # Calculate vertical velocity from depth change (central difference, cm/s)
    ddepth = -(depth[2:] - depth[:-2]) * 100  # cm
    dtime = (time[2:] - time[:-2]) / np.timedelta64(1, 's')  # s

    # Handle invalid time intervals
    dtime[(dtime == 0) | (dtime > 500)] = np.nan

    # Estimate measured vertical velocity
    w_meas = ddepth / dtime
    w_meas = np.concatenate(([np.nan], w_meas, [np.nan]))  # Pad ends with NaN

    return w_meas