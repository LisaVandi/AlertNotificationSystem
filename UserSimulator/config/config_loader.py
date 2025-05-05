import yaml
from pathlib import Path

def load_yaml_config(config_name="config.yaml"):
    config_path = Path(__file__).resolve().parent / config_name
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
