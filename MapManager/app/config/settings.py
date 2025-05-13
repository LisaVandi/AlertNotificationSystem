RABBITMQ_CONFIG = {
    "host": "localhost",
    "port": 5672, 
    "username": "guest",
    "password": "guest"
}

PATHFINDING_CONFIG = {
    "default_exit_node_types": ["outdoor", "stairs"],  # nodi target = tipi di nodi considerati punti di evacuazione o "uscite di sicurezza" nel grafo.
    "max_node_capacity": 50,  # limite oltre cui un nodo è considerato affollato
    "max_arc_capacity": 30,   # se superato, l'arco può diventare non attivo
}
