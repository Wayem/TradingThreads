import os

def get_project_root() -> str:
    current_path = os.path.abspath(__file__)
    while not os.path.isfile(os.path.join(current_path, 'root_marker.txt')):
        current_path = os.path.dirname(current_path)
    return current_path