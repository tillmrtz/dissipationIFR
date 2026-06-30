import xarray as xr
import numpy as np
import gsw
from tqdm import tqdm


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