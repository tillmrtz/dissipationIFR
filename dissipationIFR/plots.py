import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LogNorm
from matplotlib.ticker import MaxNLocator, LogLocator

import cmocean.cm as cmo
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from dissipationIFR import utilities

import pathlib
parent_dir = pathlib.Path(__file__).parent
plotting_style = parent_dir.joinpath('config/plotting.mplstyle')


def get_color_limits(values, log_scale=False):
    finite = values[np.isfinite(values)]

    if log_scale:
        finite = finite[finite > 0]

        if finite.size == 0:
            raise ValueError("No positive values available for LogNorm.")
        
        if finite.size < values.size:
            print("Warning: Some non-positive values will be ignored in log scale.")

    return (np.nanpercentile(finite, 0.5),np.nanpercentile(finite, 99.5),)

def get_contour_levels(levels=None, log_scale=False, vmin=None, vmax=None):
    # If the user passed an explicit array/list of levels, use it directly
    if levels is not None and not isinstance(levels, (int, float)):
        return levels
        
    # If levels is an integer or None, use it as the target number of intervals
    num = levels if isinstance(levels, (int, float)) else 10

    if log_scale:
        # Find clean decade limits that encompass vmin and vmax
        dec_min, dec_max  = np.floor(np.log10(vmin)), np.ceil(np.log10(vmax))
        
        # LogLocator naturally picks clean base-10 steps (e.g., 10^-5, 10^-4...)
        locator = LogLocator(base=10, numticks=2*num)
        levels = locator.tick_values(10**dec_min, 10**dec_max)
        
        # Filter levels to strictly fall within your desired vmin/vmax range
        levels = levels[(levels >= vmin) & (levels <= vmax)]
    else:
        # MaxNLocator finds clean intervals (multiples of 1, 2, 5, 10)
        locator = MaxNLocator(nbins=2*num, steps=[1, 2, 5, 10])
        levels = locator.tick_values(vmin, vmax)
        
        # Filter and append strict boundary limits
        levels = levels[(levels >= vmin) & (levels <= vmax)]

    return levels

def plot_section(ds, var, v_res=2, start=None, end=None, show_time_axis=True, method="pcolormesh", log_scale=False, ax = None, **kw,):
    """
    Plots a section of the specified variable from the dataset `ds` against depth and profile number.

    Parameters
    ----------
    ds: xarray.Dataset
        The dataset containing the variable to be plotted.
    var: str
        The name of the variable to be plotted.
    ax: matplotlib.axes.Axes, optional
        The axes on which to plot. If None, a new figure and axes will be created.
    v_res: float, optional
        The vertical resolution for the grid. Default is 2.
    start: int, optional
        The starting profile number for the section. If None, it defaults to the minimum profile number in the dataset.
    end: int, optional
        The ending profile number for the section. If None, it defaults to the maximum profile number in the dataset.
    show_time_axis: bool, optional
        Whether to show a secondary x-axis with time corresponding to the profile numbers. Default is True.
    method: str, optional
        The method to use for plotting. Options are "contourf" for filled contour plot and "pcolormesh" for a pseudocolor plot. Default is "pcolormesh".
    log_scale: bool, optional
        Whether to use a logarithmic scale for the color mapping. Default is False.
    **kw:
        Additional keyword arguments to pass to the plotting function (e.g., cmap, vmin, vmax, levels).

    Returns
    -------
    ax: matplotlib.axes.Axes
        The axes on which the section plot was created.
    cbar: matplotlib.colorbar.Colorbar
        The colorbar associated with the plot.
    time_ax: matplotlib.axes.Axes or None
        The secondary x-axis for time, if `show_time_axis` is True; otherwise, None.

    Notes
    -----
    """

    # -------------------------
    # subset profiles
    # -------------------------
    if start is not None or end is not None:
        start = ds.PROFILE_NUMBER.min() if start is None else start
        end = ds.PROFILE_NUMBER.max() if end is None else end

        mask = (ds.PROFILE_NUMBER >= start) & (ds.PROFILE_NUMBER <= end)

        dim = list(ds.dims)[0]
        ds = ds.sel({dim: mask})

    values = ds[var].values
    depth = ds.DEPTH.values
    profiles = ds.PROFILE_NUMBER.values

    if log_scale:
        values = np.where(values <= 0, np.nan, values)

    # -------------------------
    # grid
    # -------------------------
    Z, X, Y = utilities.construct_2dgrid(
        profiles,
        depth,
        values,
        1,
        v_res,
        x_bin_center=False,
    )

    if kw.get("vmin") is None or kw.get("vmax") is None:
        vmin, vmax = get_color_limits(values, log_scale=log_scale)
        if kw.get("vmin") is None:
            kw["vmin"] = vmin
        if kw.get("vmax") is None:
            kw["vmax"] = vmax

    if log_scale:
        kw["norm"] = LogNorm(vmin=kw["vmin"], vmax=kw["vmax"])

    # -------------------------
    # plotting
    # -------------------------

    with plt.style.context(plotting_style):
        # --- Handle provided axes ---
        if ax is not None:
            fig = ax.get_figure()
        else:
            # Create new figure and axes if none provided
            fig, ax = plt.subplots(figsize=(15, 5))

        if not kw.get("cmap"):
            kw["cmap"] = utilities.plotting_cmap(var)

        levels = kw.pop("levels", None)

        if method == "contourf":
            levels = get_contour_levels(levels=levels, log_scale=log_scale, vmin=kw["vmin"], vmax=kw["vmax"])
            mappable = ax.contourf(X,Y,Z,**kw,levels=levels, extend="both")

        elif method == "pcolormesh":
            if kw.get("norm"):
                kw.pop("vmin", None)
                kw.pop("vmax", None)
            mappable = ax.pcolormesh(X,Y,Z,**kw)

        else:
            raise ValueError(f"Unknown method '{method}'")

        # -------------------------
        # axes formatting
        # -------------------------
        label = utilities.plotting_labels(var)
        unit = utilities.plotting_units(ds, var)

        ax.invert_yaxis()
        ax.set_ylabel("Depth (m)")
        ax.set_xlabel("Profile Number")
        ax.set_title(f"Section plot of {label}")
        ax.grid(True)

        # -------------------------
        # colorbar
        # -------------------------
        cbar = plt.colorbar(mappable, ax=ax, spacing="proportional",extend="both")
        cbar.set_label(f"{label} [{unit}]")
        if log_scale:
            cbar.ax.set_yscale('log')

        # -------------------------
        # optional time axis
        # -------------------------
        time_ax = None
        if show_time_axis:
            df = ds[["TIME", "PROFILE_NUMBER"]].to_dataframe().dropna()

            if df.index.name == "TIME":
                df = df.reset_index()

            mean_times = (df.groupby("PROFILE_NUMBER")["TIME"].mean())

            t = mdates.date2num(pd.to_datetime(mean_times))
            p = mean_times.index.values

            to_time = interp1d(p,t,bounds_error=False,fill_value="extrapolate",)

            to_profile = interp1d(t,p,bounds_error=False,fill_value="extrapolate",)

            time_ax = ax.secondary_xaxis("bottom",functions=(to_time, to_profile),)

            time_ax.spines["bottom"].set_position(("outward", 40))

            time_ax.xaxis.set_major_locator(mdates.AutoDateLocator())

            dt = t[-1] - t[0]
            fmt = ("%Y-%m-%d %H:%M" if dt < 5 else "%Y-%m-%d")
            time_ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt))

            time_ax.tick_params(rotation=35)

    return ax, cbar, time_ax