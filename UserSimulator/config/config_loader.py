import yaml
from datetime import datetime, time
from typing import Dict, List
from UserSimulator.utils.logger import logger

class Config:
    def __init__(self, config_path: str = "UserSimulator/config/config.yaml"):
        """Initialize configuration from YAML file"""
        self.n_users: int = 20
        self.speed_normal: float = 1.5
        self.speed_alert: float = 3.0
        self.simulation_tick: float = 1.0
        self.timeout_after_stop: int = 60
        self.time_slots: List[Dict] = []
        
        
        # Valori di default per RabbitMQ
        self.rabbitmq = {
            "host": "localhost",
            "port": 5672,
            "username": "guest",
            "password": "guest",
            "alert_queue": "alert_queue",
            "evacuation_paths_queue": "evacuation_paths_queue",
            "position_queue": "position_queue",
        }

        self._load_config(config_path)

    def _load_config(self, config_path: str):
        """Load and validate configuration from YAML file"""
        try:
            with open(config_path, "r") as f:
                cfg = yaml.safe_load(f) or {}
            
            self.n_users = cfg.get("n_users", self.n_users)
            self.speed_normal = cfg.get("speed_normal", self.speed_normal)
            self.speed_alert = cfg.get("speed_alert", self.speed_alert)
            self.simulation_tick = cfg.get("simulation_tick", self.simulation_tick)
            self.timeout_after_stop = cfg.get("timeout_after_stop", self.timeout_after_stop)
            self.time_slots = cfg.get("time_slots", self.time_slots)
            self.simulation_mode = cfg.get("simulation_mode", "from_scratch")
            self.user_file = cfg.get("user_file", None)
            self.alert_event_type = cfg.get("alert_event_type", None)

            
            self._validate_config()
            logger.info(f"Configuration loaded: users={self.n_users}, tick={self.simulation_tick}s")
            
        except Exception as e:
            logger.critical(f"Config load failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Configuration error: {str(e)}") from e

    def _validate_config(self):
        """Validate configuration values"""
        if self.n_users <= 0:
            raise ValueError("n_users must be positive")
        if not self.time_slots:
            logger.warning("No time slots defined in configuration")

    def get_distribution_for_current_time(self, current_time: time = None) -> Dict:
        """Get node distribution for current time slot"""
        current_time = current_time or datetime.now().time()
        
        for slot in self.time_slots:
            try:
                start = self._parse_time(slot['start'])
                end = self._parse_time(slot['end'])
                
                if start <= current_time < end:
                    dist = slot.get('distribution', {})
                    logger.debug(f"Time {current_time.strftime('%H:%M')} matches slot {slot['start']}-{slot['end']}")
                    return dist
                    
            except KeyError as e:
                logger.warning(f"Invalid time slot format: {str(e)}")
                continue
                
        logger.info(f"No slot found for {current_time.strftime('%H:%M')}, using default")
        return {}

    @staticmethod
    def _parse_time(t_str: str) -> time:
        """Parse time string (HH:MM) into time object"""
        try:
            return datetime.strptime(t_str, "%H:%M").time()
        except ValueError as e:
            logger.error(f"Invalid time format '{t_str}': {str(e)}")
            raise ValueError(f"Time must be in HH:MM format: {t_str}") from e