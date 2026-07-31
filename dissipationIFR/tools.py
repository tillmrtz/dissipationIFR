import xarray as xr
import pandas as pd
import numpy as np
import gsw
from tqdm import tqdm
from scipy.signal import butter, filtfilt


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

# --------------------------------------------------------------------
# Calculate buoyancy frequency (Brunt-Väisälä frequency) functions
# --------------------------------------------------------------------


def calc_n(press, temp, salinity, lat, lon, rho0=1027.0, n=2):
    """
    Compute unsorted (in-situ) Brunt-Väisälä frequency using a windowed
    linear regression of density vs. depth.

    For each point, all valid (non-NaN) samples within +/- n indices are
    used to estimate the local density gradient via linear regression,
    rather than a simple two-point (i+n, i-n) finite difference. This makes
    the estimate robust to isolated NaNs in temp/salinity/press: as long as
    at least 2 valid points remain in the window, a gradient is computed.

    Parameters
    ----------
    press : 1D array
        Pressure [dbar].
    temp : 1D array
        Temperature [°C].
    salinity : 1D array
        Practical salinity [PSU].
    lat, lon : 1D array or float
        Latitude / longitude.
    rho0 : float, optional
        Reference density [kg/m^3] (default 1027.0)
    n : int, optional
        Number of points in each direction defining the window half-width
        (default 2, i.e. a 5-point window).

    Returns
    -------
    1D array
        N [1/s], same length as input, NaN where not computable.
    """
    press = np.asarray(press, dtype=float)
    temp = np.asarray(temp, dtype=float)
    salinity = np.asarray(salinity, dtype=float)

    SA = gsw.SA_from_SP(salinity, press, lon, lat)
    CT = gsw.CT_from_t(SA, temp, press)
    depth = gsw.z_from_p(press, lat)  # depth in meters (positive down)
    density = gsw.sigma0(SA, CT)

    # calc gravity at each depth and interpolate over nans
    g = gsw.grav(lat, press)
    #g = np.interp(depth, depth[~np.isnan(g)], g[~np.isnan(g)])

    n_pts = len(depth)
    n_all = np.full(n_pts, np.nan, dtype=float)

    for i in range(n_pts):
        lo = max(i - n, 0)
        hi = min(i + n + 1, n_pts)  # +1 since slice upper bound is exclusive

        z_win = depth[lo:hi]
        rho_win = density[lo:hi]

        valid = ~(np.isnan(z_win) | np.isnan(rho_win))
        if np.count_nonzero(valid) < 2:
            continue

        z_valid = z_win[valid]
        rho_valid = rho_win[valid]

        if np.var(z_valid) == 0:
            continue

        drho_dz = -np.cov(z_valid, rho_valid)[0, 1] / np.var(z_valid)

        if drho_dz < 0:
            continue  # locally unstable; N undefined here

        n_all[i] = np.sqrt((g[i] / rho0) * drho_dz)

    return n_all


def calc_n_sorted(profile_number, press, temp, salinity, lat, lon, plev=20):
    """
    Compute adiabatically-sorted Brunt-Väisälä frequency (N) for one or more
    vertical profiles concatenated into single 1D arrays.

    For each point, all samples within a +/- plev/2 pressure window (within
    the same profile) are taken, their locally-referenced potential density
    is computed, and the vertical gradient is estimated as the slope of a
    linear fit of specific volume against pressure.

    Parameters
    ----------
    profile_number : 1D array
        Profile identifier for each sample, same length as press. Samples
        sharing a profile_number are treated as one cast.
    press : 1D array
        Pressure [dbar]
    temp : 1D array
        In-situ temperature [degC]
    salinity : 1D array
        Practical salinity [PSU]
    lat, lon : 1D array or float
        Latitude / longitude for each sample (or a single scalar applied to
        all samples). If arrays, the per-profile mean is used internally.
    plev : float, optional
        Pressure window width [dbar] used for the local linear fit (default 20)

    Returns
    -------
    1D array
        N [1/s], same length as press, NaN where not computable.
    """
    profile_number = np.asarray(profile_number)
    press = np.asarray(press, dtype=float)
    temp = np.asarray(temp, dtype=float)
    salinity = np.asarray(salinity, dtype=float)

    def _calc_single_profile(press_p, temp_p, salinity_p, lat_p, lon_p):
        n_profile = np.full_like(press_p, np.nan, dtype=float)
 
        if np.all(np.isnan(press_p)):
            return n_profile
 
        SA = gsw.SA_from_SP(salinity_p, press_p, lon_p, lat_p)
        CT = gsw.CT_from_t(SA, temp_p, press_p)
        rho = gsw.rho(SA, CT, press_p)
        gravities = gsw.grav(lat_p, press_p)
 
        press_min = np.nanmin(press_p)
        press_max = np.nanmax(press_p)
 
        for jj in range(len(press_p)):
            if np.isnan(press_p[jj]):
                continue
 
            pmin_lev = np.maximum(press_p[jj] - plev / 2, press_min)
            pmax_lev = np.minimum(press_p[jj] + plev / 2, press_max)
            icyc = np.where((press_p >= pmin_lev) & (press_p <= pmax_lev))[0]

            if len(icyc) < 2:
                continue

            pbar = np.nanmean(press_p[icyc])

            pot_rho = gsw.pot_rho_t_exact(SA[icyc], temp_p[icyc], press_p[icyc], pbar)

            sv = 1 / pot_rho
            press_pas = press_p[icyc] * 1e4  # dbar -> Pa

            # Linear regression slope of specific volume vs. pressure
            x = np.sort(press_pas)
            y = np.sort(sv)[::-1]  # descending order for stable stratification
            alpha_1 = np.cov(x, y)[0, 1] / np.var(x)

            g = gravities[jj]
            if np.isnan(rho[icyc]).any():
                continue
            rhobar = np.nanmean(rho[icyc])

            n2 = rhobar ** 2 * g ** 2 * -alpha_1

            if n2 >= 0:
                n_profile[jj] = np.sqrt(n2)

        return n_profile

    n_all = np.full_like(press, np.nan, dtype=float)
    unique_profiles = np.unique(profile_number)
    for pnum in tqdm(unique_profiles):
        mask = profile_number == pnum
        if not np.any(mask):
                continue
        n_all[mask] = _calc_single_profile(
            press[mask], temp[mask], salinity[mask], lat[mask], lon[mask]
        )

    return n_all

# --------------------------------------------------------------------
# Highpass filter functions
# --------------------------------------------------------------------

def _trim_nan_edges(arr):
    """
    Trims NaN values from the beginning and end of a 1D array.

    Parameters
    ----------
    arr: np.ndarray
        Input array to be trimmed.

    Returns
    -------
    trimmed_arr: np.ndarray
        Array with NaN values trimmed from the edges.
    first: int
        Index of the first non-NaN value.
    last: int
        Index of the last non-NaN value.
    """
    is_not_nan = ~np.isnan(arr)
    if not is_not_nan.any():
        return np.array([]), 0, 0
    first = np.argmax(is_not_nan)
    last = len(arr) - np.argmax(is_not_nan[::-1])
    return arr[first:last], first, last


def _design_filter(mean_dt, cutoff_period, order):
    """Designs a highpass Butterworth filter for a given cutoff period and sampling interval.
    Returns None if the resulting critical frequency is invalid."""
    if cutoff_period is None or not np.isfinite(cutoff_period) or cutoff_period <= 0:
        return None
    fs = 1 / mean_dt
    fc = 1 / cutoff_period
    wn = 2 * fc / fs
    if not (0 < wn < 1):
        return None
    return butter(order, wn, btype='high')


def highpass_butterworth_time(var_arr, time, profile_number, cutoff_period=330, order=4,
                               max_interval=40, adaptive_window=None):
    """
    Applies a highpass Butterworth filter to a variable over time, per profile.

    Assumes input arrays are already gridded (i.e. no binning is performed).

    Parameters
    ----------
    var_arr : np.ndarray
        1D array of the variable to filter.
    time : np.ndarray
        1D array of timestamps (datetime64), same length as var_arr.
    profile_number : np.ndarray
        1D array of profile numbers, same length as var_arr.
    cutoff_period : float or np.ndarray, optional
        Highpass cutoff period in seconds (default 330s). If an array is
        given (same length as var_arr), it is treated as a spatially/
        temporally varying cutoff, and `adaptive_window` must also be set.
    order : int, optional
        Butterworth filter order (default 4).
    max_interval : float, optional
        Max gap (in seconds) to treat data as continuous (default 40s).
    adaptive_window : float, optional
        Window length in seconds. Required if cutoff_period is an array.
        Within each profile, the signal is split into windows of this
        length. For each window, the mean of cutoff_period within that
        window is used to design a Butterworth filter, which is applied
        to the full trimmed profile; only the filtered values falling
        inside that window are kept from that run.

    Returns
    -------
    np.ndarray
        Filtered array, same shape as var_arr, with NaNs where filtering
        could not be applied (gaps, edges, skipped profiles).
    """
    is_adaptive = isinstance(cutoff_period, np.ndarray)
    if is_adaptive and adaptive_window is None:
        raise ValueError("adaptive_window must be set when cutoff_period is an array.")

    filtered_full = np.full_like(var_arr, np.nan, dtype=float)

    unique_profiles = np.unique(profile_number)
    for pn in tqdm(unique_profiles, desc="Filtering"):
        mask = profile_number == pn
        signal = var_arr[mask]
        t = time[mask]

        dt = np.diff(t) / np.timedelta64(1, 's')
        dt[dt > max_interval] = np.nan
        if np.all(np.isnan(dt)):
            continue
        mean_dt = np.nanmean(dt)
        if mean_dt == 0:
            continue

        trimmed, start, end = _trim_nan_edges(signal)
        if trimmed.size == 0:
            continue

        valid = ~np.isnan(trimmed)

        # Interpolate NaNs before filtering
        if np.isnan(trimmed).any():
            trimmed = pd.Series(trimmed).interpolate(
                method='linear', limit_direction='both').values

        if is_adaptive:
            cutoff_sub = cutoff_period[mask][start:end]
            win_samples = max(1, int(round(adaptive_window / mean_dt)))

            profile_filtered = np.full_like(trimmed, np.nan, dtype=float)

            for win_start in range(0, len(trimmed), win_samples):
                win_end = min(win_start + win_samples, len(trimmed))
                win_cutoff = np.nanmean(cutoff_sub[win_start:win_end])
                #print(f"Profile {pn}, Window {win_start}-{win_end}: mean cutoff = {win_cutoff} dt: {mean_dt}")
                if np.isnan(win_cutoff):
                    continue

                result = _design_filter(mean_dt, win_cutoff, order)
                if result is None:
                    continue
                b, a = result

                if len(trimmed) <= 3 * max(len(a), len(b)):
                    continue

                filtered_run = filtfilt(b, a, trimmed)
                profile_filtered[win_start:win_end] = filtered_run[win_start:win_end]

            # profile_filtered[~valid] = np.nan

            full_profile = np.full_like(signal, np.nan, dtype=float)
            full_profile[start:end] = profile_filtered
            filtered_full[mask] = full_profile

        else:
            result = _design_filter(mean_dt, cutoff_period, order)
            if result is None:
                continue
            b, a = result

            if len(trimmed) > 3 * max(len(a), len(b)):
                filtered = filtfilt(b, a, trimmed)
                # filtered[~valid] = np.nan

                profile_filtered = np.full_like(signal, np.nan, dtype=float)
                profile_filtered[start:end] = filtered
                filtered_full[mask] = profile_filtered

    return filtered_full


# --------------------------------------------------------------------
# Rolling RMS function
# --------------------------------------------------------------------


def rolling_rms(var_arr, time, profile_number, window_size_seconds=100):
    """
    Computes the RMS of a variable in a centered rolling window, per profile.

    Assumes input arrays are already gridded (i.e. no binning is performed).

    Parameters
    ----------
    var_arr : np.ndarray
        1D array of the variable to compute RMS for.
    time : np.ndarray
        1D array of timestamps (datetime64), same length as var_arr.
    profile_number : np.ndarray
        1D array of profile numbers, same length as var_arr.
    window_size_seconds : float, optional
        Size of the time window in seconds for computing RMS (default 100s).
    max_interval : float, optional
        Max gap (in seconds) to treat data as continuous when estimating
        the mean sampling interval (default 100s).

    Returns
    -------
    np.ndarray
        RMS array, same shape as var_arr, with NaNs where insufficient
        data was available (edges, skipped profiles).
    """
    rms_full = np.full_like(var_arr, np.nan, dtype=float)

    unique_profiles = np.unique(profile_number)
    for pn in tqdm(unique_profiles, desc="Computing RMS"):
        mask = profile_number == pn
        signal = var_arr[mask]
        t = time[mask]

        if len(t) < 2:
            continue

        dt = np.diff(t) / np.timedelta64(1, 's')
        mean_dt = np.mean(dt) if len(dt) > 0 else 1.0
        if mean_dt <= 0:
            continue

        window_size = max(1, int(round(window_size_seconds / mean_dt)))

        squared = pd.Series(signal) ** 2
        mean_sq = squared.rolling(window=window_size, center=True, min_periods=1).mean()
        rms = np.sqrt(mean_sq.values)

        rms_full[mask] = rms

    return rms_full

# --------------------------------------------------------------------
# Calculate turbulent kinetic energy dissipation rate (epsilon) function
# --------------------------------------------------------------------

def calc_epsilon(velocity_rms, n, c = 1.0):
    """
    Calculates the turbulent kinetic energy dissipation rate (epsilon) from the RMS of velocity fluctuations and buoyancy frequency.

    Parameters
    ----------
    velocity_rms : np.ndarray
        1D array of RMS of velocity fluctuations (m/s).
    n : np.ndarray
        1D array of buoyancy frequency (rad/s).
    c : float, optional
        Constant of proportionality. need to be derived by comparing to microstructure measurements (default is 1.0).

    Returns
    -------
    np.ndarray
        1D array of epsilon values (W/kg), same shape as input arrays.
    """
    epsilon = c * (velocity_rms ** 2) * n
    return epsilon


# --------------------------------------------------------------------
# Calculate bathymetry levels for plotting
# --------------------------------------------------------------------


def get_bathymetry_levels(bath, level_spacing=250):
        """
        This function computes the bathymetry levels for a given bathymetry dataset.

        Parameters
        ----------
        bath: xarray.Dataset
            Bathymetry dataset with 'elevation' variable.
        level_spacing: int, optional
            The spacing between contour levels. Default is 250 m.

        Returns
        -------
        levels: numpy.ndarray
            An array of bathymetry levels.
        contour_levels: numpy.ndarray
            An array of contour levels.
        max_level: int
            The maximum bathymetry level.
        """
        max_depth = np.max(-bath.elevation.values)  # Depths are negative
        max_level = level_spacing * (np.round(max_depth / level_spacing) + 1)
        levels = np.arange(0, max_level, level_spacing)
        contour_levels = levels[::2]  # Every second level
        return levels, contour_levels, max_level