import yaml

# Function to load the filter configuration from a YAML file
def load_filter_config(config_file="config/filter_config.yaml"):
    """
    Loads the filter configuration from a YAML file.

    Parameters:
    config_file (str): The path to the YAML configuration file (default is "config/filter_config.yaml").

    Returns:
    dict: A dictionary containing the filter configuration from the YAML file.
    """
    with open(config_file, "r") as file:  # Open the YAML file in read mode
        return yaml.safe_load(file)  # Parse the YAML file and return its contents as a Python dictionary

# Function to apply the filter on a single CAP alert
def filter_alerts(cap_dict, filter_config):
    """
    Filters a CAP alert dictionary based on the filter configuration.

    Parameters:
    cap_dict (dict): The CAP alert dictionary to filter.
    filter_config (dict): The configuration dictionary containing the filter rules.

    Returns:
    bool: True if the alert matches the filter criteria, False otherwise.
    """
    # Iterate over each filter category in the configuration (e.g., event, urgency, etc.)
    for key, values in filter_config["cap_filter"].items():
        # Skip the optionalFields filter (this is handled differently)
        if key != "optionalFields":
            # Check if the value of the key in the alert matches any of the valid values in the configuration
            if cap_dict.get(key) not in values:
                return False  # If it doesn't match, return False (alert is not valid)

    # If all conditions are met, return True (alert is valid)
    return True

# Function to load the filter configuration and apply it to a list of CAP alerts
def process_cap(cap_dict, config_file="config/filter_config.yaml"):
    """
    Loads the filter configuration from a YAML file and applies it to a list of CAP alerts.

    Parameters:
    caps (list): A list of CAP alert dictionaries.
    config_file (str): Path to the filter configuration file (default is "config/filter_config.yaml").

    Returns:
    list: A list of filtered CAP alert dictionaries.
    """
    filter_config = load_filter_config(config_file)  # Load the filter configuration from the YAML file
    return filter_alerts(cap_dict, filter_config)  # Apply the filter to the alerts and return the filtered list
