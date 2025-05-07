import yaml
import os

def load_config(path="UserSimulator/config/config.yaml"):
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)
