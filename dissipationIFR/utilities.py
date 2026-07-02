import pathlib

import numpy as np
import pandas as pd
import xarray as xr

from dissipationIFR.config.variables import variables
from seagliderOG1 import readers


# --------------------------------------------------------------
# Gridding and interpolation utilities
# --------------------------------------------------------------

def regular_grid(data, res):
    """
    Create bin edges for a regular grid such that multiples of `res` fall on
    bin centers. For example, with res=5 the edges are [-2.5, 2.5, 7.5, ...]

    Parameters
    ----------
    data : array-like
        Input data used to determine the grid range.
    res : float
        Grid resolution (bin width).

    Returns
    -------
    numpy.ndarray
        Bin edges for the regular grid.
    """
    d_min = np.floor(np.nanmin(data) / res) * res + res / 2
    d_max = np.ceil(np.nanmax(data) / res) * res - res / 2
    return np.arange(d_min, d_max + res + 1, res)


def construct_2dgrid(x, y, v, xi=1, yi=1, x_bin_center: bool = True, y_bin_center: bool = True, agg: str = 'median'):

    """
    Constructs a 2D gridded representation of input data based on specified resolutions. The function takes in x, y, and v data,
    and generates a grid where each cell contains the aggregated value (e.g., mean, median) of v corresponding to the x and y coordinates.
    If the input data is already binned and you want the grid coordinates to align with the original bin edges, set `x_bin_center` and `y_bin_center` to False and the 
    resolution (i.e. xi and yi) to the bin size.

    Parameters
    ----------
    x : array-like  
        Input data representing the x-dimension.  
    y : array-like  
        Input data representing the y-dimension.  
    v : array-like  
        Input data representing the z-dimension (values to be gridded).  
    xi : int or float, optional, default=1  
        Resolution for the x-dimension grid spacing.  
    yi : int or float, optional, default=1  
        Resolution for the y-dimension grid spacing.
    x_bin_center : bool, optional, default=True
        If True, the x-coordinate grid (`XI`) corresponds to the **center** of each x-bin.
        If False, it corresponds to the **left edge** of each bin.
        This is especially useful if the input `x` data is already binned with the same resolution as `xi`,
        and you want the grid coordinates to align with the original bin edges. (e.g. profile numbers).
    y_bin_center : bool, optional, default=True
        Same as `x_bin_center`, but for the y-coordinate grid (`YI`).
        Set to False if your `y` data is already pre-binned with the same resolution as `yi`.
    agg : str, optional, default='median'
        Aggregation method to be used for gridding. Options include 'mean', 'median', etc.

    Returns
    -------
    grid : numpy.ndarray  
        Gridded representation of the z-values over the x and y space.  
    XI : numpy.ndarray  
        Gridded x-coordinates corresponding to the specified resolution.  
    YI : numpy.ndarray  
        Gridded y-coordinates corresponding to the specified resolution. 

    Notes
    -----
    Original Author: Bastien Queste
    [Source Code](https://github.com/bastienqueste/gliderad2cp/blob/de0652f70f4768c228f83480fa7d1d71c00f9449/gliderad2cp/process_adcp.py#L140)
    
    Modified by Till Moritz: added the aggregation parameter and the option to chose either bin center or bin edge as the grid coordinates.
    """
    if np.size(xi) == 1:
        xi = np.arange(np.nanmin(x), np.nanmax(x) + xi+1, xi)
    if np.size(yi) == 1:
        yi = np.arange(np.nanmin(y), np.nanmax(y) + yi+1, yi)

    raw = pd.DataFrame({'x': x, 'y': y, 'v': v}).dropna()
    grid = np.full([len(xi)-1, len(yi)-1], np.nan)

    raw['xbins'], xbin_iter = pd.cut(raw.x, xi, retbins=True, labels=False, include_lowest=True, right=False)
    raw['ybins'], ybin_iter = pd.cut(raw.y, yi, retbins=True, labels=False, include_lowest=True, right=False)

    raw = raw.dropna(subset=['xbins', 'ybins'])  # Remove out-of-bound rows
    _tmp = raw.groupby(['xbins', 'ybins'])['v'].agg(agg)
    grid[_tmp.index.get_level_values(0).astype(int), _tmp.index.get_level_values(1).astype(int)] = _tmp.values
    # Match XI and YI shape to grid using bin centers
    if x_bin_center:
        xi = xi[:-1] + np.diff(xi) / 2
    else:
        xi = xi[:-1]
    if y_bin_center:
        yi = yi[:-1] + np.diff(yi) / 2
    else:
        yi = yi[:-1]
    YI, XI = np.meshgrid(yi, xi)
    return grid, XI, YI


def to_numeric(arr):
    """
    Convert datetime64 arrays to seconds relative to the first value.

    Returns
    -------
    numeric : ndarray
    dtype : dtype or None
    reference : datetime64 or None
    """
    if np.issubdtype(arr.dtype, np.datetime64):
        reference = arr[0]
        numeric = (arr - reference) / np.timedelta64(1, "s")
        return numeric.astype(float), arr.dtype, reference

    return arr, None, None


def from_numeric(arr, dtype, reference):
    """
    Convert numeric arrays back to their original dtype.
    """
    if dtype is None:
        return arr

    return reference + (arr * np.timedelta64(1, "s")).astype("timedelta64[s]")

def interpolate_over_nans(da, dim="N_MEASUREMENTS", method="linear"):
    """
    Interpolate over NaNs in a DataArray along the given dimension.
    Works for numeric and datetime64 arrays alike.
    """
    if np.issubdtype(da.dtype, np.datetime64):
        reference = da.values[0]
        numeric_values = (da.values - reference) / np.timedelta64(1, "s")
        numeric = xr.DataArray(numeric_values, dims=[dim])
        numeric = numeric.interpolate_na(dim=dim, method=method)
        result_values = reference + (numeric.values * np.timedelta64(1, "s")).astype("timedelta64[s]")
        return xr.DataArray(result_values, dims=[dim])

    return da.interpolate_na(dim=dim, method=method)


def grid_dataset(ds, variables, bin_variable="DEPTH", res=5, agg="median"):
    """
    Grid a dataset along profiles.

    Datetime variables are internally converted to seconds relative to the
    first sample of each profile before gridding and converted back afterwards.
    """

    required_vars = [
        "TIME",
        "DEPTH",
        "LONGITUDE",
        "LATITUDE",
        "PROFILE_NUMBER",
    ]

    coord_vars = ["TIME", "DEPTH", "LONGITUDE", "LATITUDE", bin_variable]

    all_vars = list(dict.fromkeys(required_vars + list(variables)))
    vars_to_grid = [v for v in all_vars if v not in (bin_variable, "PROFILE_NUMBER")]

    profile_numbers = ds.PROFILE_NUMBER.values
    unique_profiles = np.unique(profile_numbers)

    gridded_vars = {}

    profile_number_flat = None
    bin_variable_flat = None

    for var in vars_to_grid:

        var_chunks = []
        profile_chunks = []
        bin_chunks = []

        var_all = ds[var].values
        bin_all = ds[bin_variable].values

        for profile in unique_profiles:

            mask = profile_numbers == profile

            # ---- Extract one profile ----
            var_profile, var_dtype, var_ref = to_numeric(var_all[mask])
            bin_profile, bin_dtype, bin_ref = to_numeric(bin_all[mask])

            # ---- Common grid ----
            if res is not None:
                yi = regular_grid(bin_profile, res)
            else:
                yi = abs(np.nanmean(np.diff(bin_profile)))

            grid_var, xi_grid, yi_grid = construct_2dgrid(
                profile_numbers[mask],
                bin_profile,
                var_profile,
                xi=1,
                yi=yi,
                x_bin_center = False,
                agg=agg,
            )
            if np.nanmean(np.diff(bin_profile)) < 0:
                grid_var = grid_var[:, ::-1]
                xi_grid = xi_grid[:, ::-1]
                yi_grid = yi_grid[:, ::-1]

            var_chunks.append(
                from_numeric(grid_var.ravel(), var_dtype, var_ref)
            )

            profile_chunks.append(xi_grid.ravel())

            if bin_variable_flat is None:
                bin_chunks.append(
                    from_numeric(yi_grid.ravel(), bin_dtype, bin_ref)
                )

        gridded_vars[var] = np.concatenate(var_chunks)

        if profile_number_flat is None:
            profile_number_flat = np.concatenate(profile_chunks)

        if bin_variable_flat is None:
            bin_variable_flat = np.concatenate(bin_chunks)

    gridded_vars["PROFILE_NUMBER"] = profile_number_flat
    gridded_vars[bin_variable] = bin_variable_flat

    # ------------------------------------------------------------------
    # Build output dataset
    # ------------------------------------------------------------------

    dim = "N_MEASUREMENTS"
    n_measurements = len(profile_number_flat)

    data_vars = {
        var: (dim, values)
        for var, values in gridded_vars.items()
        if var not in coord_vars
    }

    ds_gridded = xr.Dataset(data_vars)

    for coord in coord_vars:
        if coord in gridded_vars:
            ds_gridded.coords[coord] = (dim, gridded_vars[coord])

    ds_gridded = ds_gridded.set_coords(
        [c for c in coord_vars if c in ds_gridded]
    )

    # ------------------------------------------------------------------
    # Copy metadata
    # ------------------------------------------------------------------

    for var in ds_gridded.variables:
        if var in ds:
            ds_gridded[var].attrs = dict(ds[var].attrs)

    ds_gridded.attrs = dict(ds.attrs)
    ds_gridded.attrs["gridding_bin_variable"] = bin_variable
    ds_gridded.attrs["gridding_resolution"] = (
        res if res is not None else "auto"
    )

    # ------------------------------------------------------------------
    # Interpolate over NaNs in coordinate variables
    # ------------------------------------------------------------------

    for coord in coord_vars:
        if coord in ds_gridded.coords:
            ds_gridded.coords[coord] = interpolate_over_nans(
                ds_gridded[coord], dim=dim
            )

    return ds_gridded

# --------------------------------------------------------------
# Functions for getting labels/ units from the variables dictionary
# --------------------------------------------------------------

def plotting_labels(var: str):
    """
    Retrieves the label associated with a variable from a predefined dictionary.

    Parameters
    ----------
    var: str
        The variable (key) whose label is to be retrieved.

    Returns
    -------
    str: 
        The label corresponding to the variable `var`. If the variable is not found in `label_dict`,
        the function returns the variable name as the label.
    """
    if var in variables:
        label = f'{variables[var]["attributes"]["long_name"]}'
    else:
        label= f'{var}'
    return label


def plotting_units(ds: xr.Dataset,var: str):
    """
    Retrieves the units associated with a variable from a dataset or a predefined dictionary.

    Parameters
    ----------
    ds: xarray.Dataset
        The dataset containing the variable `var`.
    var: str 
        The variable (key) whose units are to be retrieved.

    Returns
    -------
    str: 
        The units corresponding to the variable `var`. If the variable is found in `variables`,
        the associated units will be returned. If not, the function returns the units from `ds[var]`.
    """
    if var in variables:
        return f'{variables[var]["attributes"]["units"]}'
    elif 'units' in ds[var].attrs:
        return f'{ds[var].units}'
    else:
        return ""
    
    
def plotting_cmap(var: str):
    """
    Retrieves the colormap associated with a variable from a predefined dictionary.

    Parameters
    ----------
    var: str
        The variable (key) whose colormap is to be retrieved.

    Returns
    -------
    colormap:
        The colormap corresponding to the variable `var`. If the variable is not found in `variables`,
        the function returns None.
    """
    if var in variables:
        return variables[var]['colormap']
    else:
        return "viridis"


# --------------------------------------------------------------
# Helpers for the load and convert script and interactive CLI
# --------------------------------------------------------------


def get_mission_dives(mission_path: pathlib.Path) -> int | None:
    """
    List valid files in a mission folder and return the max dive number,
    or None if no valid files are found.

    Parameters:
    -----------
    mission_path (Path):
        Path to a single mission folder, e.g. /data/103/20070218/

    Returns:
    --------
    int | None:
        Maximum dive/profile number found, or None if folder has no valid files.
    """
    files          = readers.list_files(str(mission_path))
    filtered_files = readers.filter_files_by_profile(files)
    if not filtered_files:
        return None
    dive_numbers = [readers._profnum_from_filename(f) for f in filtered_files]
    dive_numbers = [d for d in dive_numbers if d is not None]
    return max(dive_numbers) if dive_numbers else None


def discover_all_missions(data_dir: pathlib.Path) -> dict[str, list[dict]]:
    """
    Walk data_dir and discover all valid glider/mission folders.

    Expected structure:
        data_dir/
            glider_sn/
                mission_date/
                    *.nc

    Parameters:
    -----------
    data_dir (str | Path):
        Root directory containing glider subfolders.

    Returns:
    --------
    dict:
        Structured as:
            {
                'glider_sn': [
                    {'mission': '20070218', 'path': Path(...), 'dives': 679},
                    ...
                ],
                ...
            }
        Only missions containing valid basestation .nc files are included.
    """
    data_dir   = pathlib.Path(data_dir)
    discovered = {}

    for glider_dir in sorted(data_dir.iterdir()):
        if not glider_dir.is_dir():
            continue
        missions = []
        for mission_dir in sorted(glider_dir.iterdir()):
            if not mission_dir.is_dir():
                continue
            n_dives = get_mission_dives(mission_dir)
            if n_dives is not None:
                missions.append({
                    'mission': mission_dir.name,   # e.g. '20070218'
                    'path'   : mission_dir,
                    'dives'  : n_dives,
                })
        if missions:
            discovered[glider_dir.name] = missions  # e.g. '103'

    return discovered