import yaml
import ipywidgets as widgets
from IPython.display import display, clear_output


def load_glider_config(yaml_path):
    with open(yaml_path, 'r') as file:
        return yaml.safe_load(file)


def interactive_glider_selection(yaml_path):
    """
    Interactive function that displays all gliders and their dedicated missions. After confirming both statements,
    a directory with the url and the glider mission information is returned.

    Parameters:
    yaml_path (str): The path of the yaml file that summarizes the server url and each glider mission of interest

    Returns:
    dict: A dictionary that contains the exact server url to the glider's mission and it's information
    """
    config = load_glider_config(yaml_path)
    server_url = config['data_folder']
    gliders = config['gliders']
    
    glider_names = [glider['name'] for glider in gliders]
    glider_dropdown = widgets.Dropdown(options=glider_names, description='Select Glider:')
    mission_dropdown = widgets.Dropdown(options=['Select a glider first'], description='Select Mission:', disabled=True)
    
    path_output = {'path': None,'dives': None,'glider':None,'mission':None}

    def update_missions(change):
        selected_glider = change['new']
        glider_info = next(glider for glider in gliders if glider['name'] == selected_glider)
        missions = [f"{m['date']} (dives: {m['dives']})" for m in glider_info['missions'] if m.get('folder') != 'no folder']
        
        if missions:
            mission_dropdown.options = missions
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
            mission_folder = next(
                mission['folder']
                for glider in gliders if glider['name'] == selected_glider
                for mission in glider['missions']
                if f"{mission['date']} (dives: {mission['dives']})" == selected_mission
            )
            path_output['path'] = f"{server_url}{mission_folder}/"
            path_output['dives'] = int(selected_mission.split('dives: ')[1].replace(')', ''))
            path_output['glider'] = selected_glider
            path_output['mission'] = mission_folder.split('/')[1]
        
        clear_output()
        display(glider_dropdown, mission_dropdown, confirm_button)
        print(f"Selected Path: {path_output['path']}")

    glider_dropdown.observe(update_missions, names='value')
    confirm_button = widgets.Button(description="Confirm Selection")
    confirm_button.on_click(confirm_selection)

    display(glider_dropdown, mission_dropdown, confirm_button)
    
    return path_output