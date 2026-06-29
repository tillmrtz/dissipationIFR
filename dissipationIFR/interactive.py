import ipywidgets as widgets
from IPython.display import display, clear_output
import os
import warnings
from seagliderOG1 import readers
import pathlib

def interactive_glider_selection(data_dir):
    """
    Interactive function that displays all gliders and their dedicated missions discovered
    directly from the filesystem. Only folders matching the structure glider_sn/mission/*.nc
    are considered. After confirming the selection, a dictionary with the mission path and
    metadata is returned.

    Parameters:
    -----------
    data_dir (str | Path):
        The root directory where glider data is stored, expected structure:
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

    ### Check if directory exists
    if not data_dir.exists():
        raise FileNotFoundError(f"The specified directory does not exist: {data_dir}")

    ### Discover glider_sn/mission folders that contain valid .nc files
    def get_mission_dives(mission_path):
        """List valid files in mission folder and return max dive number, or None if empty."""
        files = readers.list_files(str(mission_path))
        filtered_files = readers.filter_files_by_profile(files)
        if not filtered_files:
            return None
        dive_numbers = [
            readers._profnum_from_filename(f)
            for f in filtered_files
        ]
        dive_numbers = [d for d in dive_numbers if d is not None]
        return max(dive_numbers) if dive_numbers else None

    # Build structure: {glider_sn: [{mission, path, dives}, ...]}
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
                    'mission': mission_dir.name,       # e.g. '20080606'
                    'path': mission_dir,
                    'dives': n_dives,
                })
        if missions:
            discovered[glider_dir.name] = missions     # e.g. '015'

    ### Warn and exit early if nothing found
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
    first_glider_name  = next(iter(discovered))
    first_missions     = discovered[first_glider_name]
    first_mission      = first_missions[0]

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
        missions = discovered[selected_glider]
        labels = [mission_label(m) for m in missions]

        if labels:
            mission_dropdown.options = labels
            mission_dropdown.disabled = False
        else:
            mission_dropdown.options = ['No available missions']
            mission_dropdown.disabled = True

    def confirm_selection(b):
        selected_glider  = glider_dropdown.value
        selected_label   = mission_dropdown.value

        if selected_label == 'No available missions':
            path_output['path'] = None
        else:
            missions   = discovered[selected_glider]
            labels     = [mission_label(m) for m in missions]
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