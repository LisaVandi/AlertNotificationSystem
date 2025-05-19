RABBITMQ_CONFIG = {
    "host": "localhost",
    "port": 5672, 
    "username": "guest",
    "password": "guest"
}

PATHFINDING_CONFIG = {
    "default_exit_node_types": ["outdoor"], # Node types considered as evacuation points or exits
    "max_node_capacity": 50, # Capacity limit above which a node is considered overcrowded
    "max_arc_capacity": 30 # Capacity limit above which an arc may become inactive  
}
