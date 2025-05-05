import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

# ALERTED_USERS_FILE = os.getenv("ALERTED_USERS_FILE", "PERCORSO SPECIFICATO CON BEATRICE") # Serve?
FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "") # Firebase Cloud Messaging server key

ALERT_QUEUE = "alert_queue" # queue used to receive alerts
MAP_MANAGER_QUEUE = "map_manager_queue" # coda per ricevere id_utente allertato in formato aggregato sulla base del nodo e dell'arco dal gestore delle posizioni 
USER_SIMULATOR_QUEUE = "userSimulator_queue" # queue used to ask for position requests AND stopping alert. 
POSITION_QUEUE = "position_queue" # queue used to send positions from the user simulator to the position manager
ALERTED_USERS_QUEUE = "alerted_users_queue" # queue used to send alerted users from the position manager to the Notification Center
EVACUATION_PATHS_QUEUE = "evacuation_paths_queue" # queue used to send evacuation paths from the Notification Center to the user simulator

DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "subscription_db",
    "user": "postgres",
    "password": "postgres"
}
