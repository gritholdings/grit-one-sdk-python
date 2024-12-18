import os
import json

def load_credential(key_name: str) -> str:
    with open(os.getcwd() + '/credentials.json') as f:
        credentials = json.load(f)
        return credentials[key_name]

def set_environ_credential(key_name: str) -> None:
    os.environ[key_name] = load_credential(key_name)
    return None