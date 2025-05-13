import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "") # Firebase Cloud Messaging server key

# Queue for receiving alerts from the Alert Manager to the Notification Center
ALERT_QUEUE = "alert_queue"

# Queue for receiving aggregated user IDs based on nodes and arcs from the Position Manager
MAP_MANAGER_QUEUE = "map_manager_queue"

# Queue for sending position requests and stop alert signals to the User Simulator
USER_SIMULATOR_QUEUE = "user_simulator_queue" 

# Queue for transmitting positions from the User Simulator to the Position Manager
POSITION_QUEUE = "position_queue"

# Queue for sending alerted users' IDs and evacuation paths from the Position Manager to the Notification Center
ALERTED_USERS_QUEUE = "alerted_users_queue"

# Queue for sending evacuation paths from the Notification Center to the User Simulator
EVACUATION_PATHS_QUEUE = "evacuation_paths_queue" 

DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "subscription_db",
    "user": "postgres",
    "password": "postgres"
}
