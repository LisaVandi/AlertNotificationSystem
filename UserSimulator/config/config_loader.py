import yaml

def load_config(config_path="UserSimulator/config/config.yaml"):
    """Carica la configurazione dal file YAML."""
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config
