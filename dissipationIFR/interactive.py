import os
import pathlib
import warnings

import ipywidgets as widgets
from IPython.display import display, clear_output

from dissipationIFR.utilities import discover_all_missions


def interactive_glider_selection(data_dir):
    """
    Interactive widget that displays all gliders and their dedicated missions
    discovered directly from the filesystem. Only folders matching the structure
    glider_sn/mission/*.nc are considered. After confirming the selection, a
    dictionary with the mission path and metadata is returned.

    Parameters:
    -----------
    data_dir (str | Path):
        Root directory where glider data is stored:
            data_dir/
                glider_sn/
                    mission_date/*.nc
        e.g.    103/
                    20070218/*.nc

    Returns:
    --------
    dict:
        A dictionary with keys: 'path', 'dives', 'glider', 'mission'
    """
    data_dir = pathlib.Path(data_dir)

    if not data_dir.exists():
        raise FileNotFoundError(f"The specified directory does not exist: {data_dir}")

    discovered = discover_all_missions(data_dir)

    if not discovered:
        warnings.warn(
            f"No valid glider/mission/*.nc structure found in: {data_dir}",
            UserWarning,
            stacklevel=2,
        )
        return {'path': None, 'dives': None, 'glider': None, 'mission': None}

    ### Helper: format a mission dict as a dropdown label
    def mission_label(m):
        # Convert '20080606' → '06/08' for readability
        date_str = f"{m['mission'][4:6]}/{m['mission'][2:4]}"
        return f"{date_str} (dives: {m['dives']})"

    ### Pre-select first glider and its first mission
    first_glider_name = next(iter(discovered))
    first_missions    = discovered[first_glider_name]
    first_mission     = first_missions[0]

    glider_dropdown = widgets.Dropdown(
        options=list(discovered.keys()),
        description='Select Glider:',
    )

    first_mission_labels = [mission_label(m) for m in first_missions]
    mission_dropdown = widgets.Dropdown(
        options=first_mission_labels,
        description='Select Mission:',
        disabled=False,
    )

    path_output = {
        'path'   : str(first_mission['path']) + os.sep,
        'dives'  : first_mission['dives'],
        'glider' : first_glider_name,
        'mission': first_mission['mission'],
    }

    def update_missions(change):
        selected_glider = change['new']
        missions        = discovered[selected_glider]
        labels          = [mission_label(m) for m in missions]

        if labels:
            mission_dropdown.options  = labels
            mission_dropdown.disabled = False
        else:
            mission_dropdown.options  = ['No available missions']
            mission_dropdown.disabled = True

    def confirm_selection(b):
        selected_glider = glider_dropdown.value
        selected_label  = mission_dropdown.value

        if selected_label == 'No available missions':
            path_output['path'] = None
        else:
            missions    = discovered[selected_glider]
            labels      = [mission_label(m) for m in missions]
            mission_obj = missions[labels.index(selected_label)]

            path_output['path']    = str(mission_obj['path']) + os.sep
            path_output['dives']   = mission_obj['dives']
            path_output['glider']  = selected_glider
            path_output['mission'] = mission_obj['mission']

        clear_output()
        display(glider_dropdown, mission_dropdown, confirm_button)
        print(f"Selected Path: {path_output['path']}")

    glider_dropdown.observe(update_missions, names='value')
    confirm_button = widgets.Button(description="Confirm Selection")
    confirm_button.on_click(confirm_selection)

    display(glider_dropdown, mission_dropdown, confirm_button)

    return path_output


def interactive_cli(data_dir: pathlib.Path, discovered: dict) -> dict:
    """Terminal prompt fallback for glider/mission selection."""
    glider_names = list(discovered.keys())

    print("\nAvailable gliders:")
    for i, name in enumerate(glider_names):
        print(f"  [{i}] {name}")

    while True:
        try:
            idx = int(input(f"Select glider [0-{len(glider_names)-1}]: "))
            if 0 <= idx < len(glider_names):
                break
        except ValueError:
            pass
        print("  Invalid input, try again.")

    selected_glider = glider_names[idx]
    missions        = discovered[selected_glider]

    print(f"\nAvailable missions for glider {selected_glider}:")
    for i, m in enumerate(missions):
        print(f"  [{i}] {m['mission']}  (dives: {m['dives']})")

    while True:
        try:
            idx = int(input(f"Select mission [0-{len(missions)-1}]: "))
            if 0 <= idx < len(missions):
                break
        except ValueError:
            pass
        print("  Invalid input, try again.")

    selected = missions[idx]
    return {
        'path'   : str(selected['path']) + os.sep,
        'dives'  : selected['dives'],
        'glider' : selected_glider,
        'mission': selected['mission'],
    }