import os

DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "map_position_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

RABBITMQ_CONFIG = {
    "host": os.getenv("RABBITMQ_HOST", "localhost"),
    "port": int(os.getenv("RABBITMQ_PORT", 5672)),
    "username": os.getenv("RABBITMQ_USERNAME", "guest"),
    "password": os.getenv("RABBITMQ_PASSWORD", "guest"),
    "queue_name": os.getenv("MAP_MANAGER_QUEUE", "MAP_MANAGER_QUEUE")
}

PATHFINDING_CONFIG = {
    "default_exit_node_types": ["outdoor", "stairs"],  # nodi target = tipi di nodi considerati punti di evacuazione o "uscite di sicurezza" nel grafo.
    "max_node_capacity": 50,  # limite oltre cui un nodo è considerato affollato
    "max_arc_capacity": 30,   # se superato, l'arco può diventare non attivo
}
