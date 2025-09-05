from pathlib import Path

RABBITMQ_CONFIG = {
    "host": "localhost",
    "port": 5672, 
    "username": "guest",
    "password": "guest"
}

PATHFINDING_CONFIG = {
    "default_exit_node_types": ["outdoor"], # Node types considered as evacuation points or exits
    "max_node_capacity": 50, # Capacity limit above which a node is considered overcrowded
    "max_arc_capacity": 30, # Capacity limit above which an arc may become inactive  
    "stair_xy_tolerance": 60.0
}

STAIR_CONFIG = {
    "max_connected_floors": 3,  
    "traversal_time_per_floor": 30  
}

MAP_MANAGER_QUEUE = "map_manager_queue"
ACK_EVACUATION_QUEUE = "ack_evacuation_computed"
MAP_ALERTS_QUEUE = "map_alerts_queue" # Notification Center -> MapManager

# Percorso assoluto al file alerts.yaml, indipendente dalla cartella da cui lanci il processo
ALERTS_CONFIG_PATH = str(Path(__file__).with_name("alerts.yaml"))

EVENT_TTL_SECONDS = 60   # es. 60s; regola a piacere
