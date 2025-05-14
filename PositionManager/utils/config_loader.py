import yaml
import os

from PositionManager.utils.logger import logger

CONFIG_PATH = os.path.join('PositionManager', 'config', 'config.yaml')

class ConfigLoader:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = config_path
        self.config = self._load_config()
        self.threshold = self.config.get("dispatch_threshold", 10)
        self.emergencies = self.config.get("emergencies", {})

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info("Configuration loaded successfully.")
                return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def is_user_in_danger(self, event, position):
        """
        position: dict with keys: x, y, z
        """
        event_rule = self.emergencies.get(event)
        if not event_rule:
            logger.warning(f"No rule defined for event: {event}")
            return False

        rule_type = event_rule.get("type")
        x, y, z = position["x"], position["y"], position["z"]

        if rule_type == "all":
            return True
        elif rule_type == "floor":
            floor_ranges = {
                0: range(0, 151),
                1: range(151, 301),
                2: range(301, 451),
            }
            user_floor = None
            for floor, z_range in floor_ranges.items():
                if z in z_range:
                    user_floor = floor
                    break
            if user_floor is not None:
                return user_floor in event_rule.get("danger_floors", [])
        elif rule_type == "zone":
            zone = event_rule.get("danger_zone", {})
            in_x = zone.get("x1", -1) <= x <= zone.get("x2", float('inf'))
            in_y = zone.get("y1", -1) <= y <= zone.get("y2", float('inf'))
            in_z = zone.get("z1", -1) <= z <= zone.get("z2", float('inf'))
            return in_x and in_y and in_z

        return False
