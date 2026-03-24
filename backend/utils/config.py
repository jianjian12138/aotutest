import os
import yaml
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = os.path.join(BASE_DIR, 'config.yaml')

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

config_data = load_config()

def get_config(key_path, default=None):
    """
    Get nested config value using dot notation, e.g., 'server.backend_port'
    """
    keys = key_path.split('.')
    val = config_data
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return default
    return val
