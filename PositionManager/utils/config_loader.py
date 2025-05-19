import yaml
import os
from PositionManager.utils.logger import logger

# Path to the configuration file
CONFIG_PATH = os.path.join('PositionManager', 'config', 'config.yaml')

class ConfigLoader:
    """
    This class loads and processes the configuration for the Position Manager.
    It provides methods to load the configuration from a YAML file and determine
    if a user is in danger based on the event and position data.
    
    Attributes:
        config_path (str): Path to the configuration file.
        config (dict): The loaded configuration data.
        threshold (int): Dispatch threshold for the number of messages to process.
        emergencies (dict): Emergency event rules configured in the YAML file.
    """

    def __init__(self, config_path=CONFIG_PATH):
        """
        Initializes the ConfigLoader instance by loading the configuration file 
        and extracting relevant settings.

        Args:
            config_path (str): Path to the YAML configuration file. Default is 'PositionManager/config/config.yaml'.
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.threshold = self.config.get("dispatch_threshold", 10)
        self.emergencies = self.config.get("emergencies", {})

    def _load_config(self):
        """
        Loads the configuration data from the YAML file.

        Returns:
            dict: The configuration data loaded from the file, or an empty dictionary in case of error.
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info("Configuration loaded successfully.")
                return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def is_user_in_danger(self, event, position, floor_level=None):
        """
        Determines if a user is in danger based on the event type and position.

        Args:
            event (str): The type of emergency event.
            position (dict): A dictionary containing 'x', 'y', and 'z' coordinates of the user's position.

        Returns:
            bool: True if the user is in danger, False otherwise.
        """
        # Get the event rule from the configuration
        event_rule = self.emergencies.get(event)
        
        # If no rule is found for the event, log a warning and return False
        if not event_rule:
            logger.warning(f"No rule defined for event: {event}")
            return False

        # Extract the event rule type and user's position
        rule_type = event_rule.get("type")
        x, y, z = position["x"], position["y"], position["z"]

        # Evaluate if the user is in danger based on the event rule type
        if rule_type == "all":
            return True  # All users are in danger for this event
        elif rule_type == "zone":
            zone = event_rule.get("danger_zone", {})
            in_x = zone.get("x1", -1) <= x <= zone.get("x2", float('inf'))
            in_y = zone.get("y1", -1) <= y <= zone.get("y2", float('inf'))
            in_z = zone.get("z1", -1) <= z <= zone.get("z2", float('inf'))
            return in_x and in_y and in_z

        return False  # Default: user is not in danger
