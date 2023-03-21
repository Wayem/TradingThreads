import os
import getpass
import yaml
from pykeepass import PyKeePass

KP_KEYS = ['BNB_API_KEY', 'BNB_SECRET_KEY', 'INFLUXDB_TOKEN']

with open('params.yaml', 'r') as f:
    params = yaml.safe_load(f)

def extract_kp_secrets():

    kp_password = getpass.getpass("Veuillez entrer le mot de passe principal Keepass : ")
    database_path = params['keepass_database_path']
    assert os.path.isfile(database_path)
    keepass = PyKeePass(database_path, password=kp_password)
    
    kp_secrets = {key: None for key in KP_KEYS}
    for key in KP_KEYS:
        entry = keepass.find_entries(title=key, first = True)
        kp_secrets[key] = entry.password

    assert None not in kp_secrets.values()
    return kp_secrets