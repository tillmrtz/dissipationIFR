import yaml
import ipywidgets as widgets
from IPython.display import display, clear_output
import os
import warnings


def load_glider_config(yaml_path):
    with open(yaml_path, 'r') as file:
        return yaml.safe_load(file)


def interactive_glider_selection(data_dir, yaml_path):
    """
    Interactive function that displays all gliders and their dedicated missions. After confirming both statements,
    a directory with the url and the glider mission information is returned.
    Only gliders and missions that physically exist in the given directory are shown.

    Parameters:
    -----------
    data_dir (str): 
        The directory where the glider data is stored
    yaml_path (str): 
        The path of the yaml file that summarizes the server url and each glider mission of interest

    Returns:
    --------
    dict: 
        A dictionary that contains the exact server url to the glider's mission and it's information
    """
    ### Check if directory exists
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"The specified directory does not exist: {data_dir}")

    config = load_glider_config(yaml_path)
    gliders = config['gliders']

    ### Filter: only keep gliders whose folder exists on disk
    def glider_exists(glider):
        return os.path.isdir(os.path.join(data_dir, glider['name']))

    def mission_exists(glider, mission):
        if mission.get('folder') == 'no folder':
            return False
        mission_path = os.path.join(data_dir, mission['folder'])
        return os.path.isdir(mission_path)

    available_gliders = [g for g in gliders if glider_exists(g)]

    ### Warn and exit early if no gliders are found on disk
    if not available_gliders:
        warnings.warn(
            f"No gliders from the config were found in: {data_dir}\n"
            f"Expected one or more of: {[g['name'] for g in gliders]}",
            UserWarning,
            stacklevel=2
        )
        return {'path': None, 'dives': None, 'glider': None, 'mission': None}
    
    ### Pre-select first glider and its first available mission
    first_glider = available_gliders[0]
    first_missions = [m for m in first_glider['missions'] if mission_exists(first_glider, m)]
    first_mission = first_missions[0] if first_missions else None

    glider_names = [g['name'] for g in available_gliders]
    glider_dropdown = widgets.Dropdown(options=glider_names, description='Select Glider:')

    ### Initialise mission dropdown with first glider's missions directly
    first_mission_labels = [f"{m['date']} (dives: {m['dives']})" for m in first_missions]
    mission_dropdown = widgets.Dropdown(options=first_mission_labels if first_mission_labels else ['No available missions'],
        description='Select Mission:',disabled=not bool(first_mission_labels))

    if first_mission:
        path_output = {'path': os.path.join(data_dir, first_mission['folder']) + os.sep,
            'dives': int(first_mission['dives']),'glider': first_glider['name'],'mission': first_mission['folder'].split('/')[1]}
    else:
        path_output = {'path': None, 'dives': None, 'glider': None, 'mission': None}

    def update_missions(change):
        selected_glider = change['new']
        glider_info = next(g for g in available_gliders if g['name'] == selected_glider)

        ### Filter: only missions whose folder exists on disk
        available_missions = [
            m for m in glider_info['missions']
            if mission_exists(glider_info, m)
        ]
        mission_labels = [f"{m['date']} (dives: {m['dives']})" for m in available_missions]

        if mission_labels:
            mission_dropdown.options = mission_labels
            mission_dropdown.disabled = False
        else:
            mission_dropdown.options = ['No available missions']
            mission_dropdown.disabled = True

    def confirm_selection(b):
        selected_glider = glider_dropdown.value
        selected_mission = mission_dropdown.value

        if selected_mission in ['No available missions', 'Select a glider first']:
            path_output['path'] = None
        else:
            glider_info = next(g for g in available_gliders if g['name'] == selected_glider)
            mission_obj = next(
                m for m in glider_info['missions']
                if f"{m['date']} (dives: {m['dives']})" == selected_mission
            )
            path_output['path'] = os.path.join(data_dir, mission_obj['folder']) + os.sep
            path_output['dives'] = int(mission_obj['dives'])
            path_output['glider'] = selected_glider
            path_output['mission'] = mission_obj['folder'].split('/')[1]

        clear_output()
        display(glider_dropdown, mission_dropdown, confirm_button)
        print(f"Selected Path: {path_output['path']}")

    glider_dropdown.observe(update_missions, names='value')
    confirm_button = widgets.Button(description="Confirm Selection")
    confirm_button.on_click(confirm_selection)

    display(glider_dropdown, mission_dropdown, confirm_button)

    return path_output