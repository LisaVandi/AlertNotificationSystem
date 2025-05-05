import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
ALERTED_USERS_FILE = os.getenv("ALERTED_USERS_FILE", "PERCORSO SPECIFICATO CON BEATRICE") # Placeholder for the actual path to the file
FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "")
ALERT_QUEUE = "alert_queue"
MAP_MANAGER_QUEUE = "map_queue"
USER_SIMULATOR_QUEUE = "userSimulator_queue"
POSITION_REQUEST_QUEUE = "position_request_queue"
EVACUATION_PATHS_QUEUE = "evacuation_paths_queue"

DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "subscription_db",
    "user": "postgres",
    "password": "postgres"
}
