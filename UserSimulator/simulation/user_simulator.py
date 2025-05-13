import random
import pika
import json
from MapViewer.db.db_connection import create_connection
from UserSimulator.rabbitmq.rabbitmq_manager import get_rabbitmq_channel
from UserSimulator.utils.logger import logger
from datetime import datetime
import yaml

# Variabile globale per tenere traccia dell'ultimo user_id
user_id_counter = 0  # Partiamo da un ID base
simulation_active = True  # Variabile globale per gestire lo stato della simulazione

def load_config(config_path="UserSimulator/config/config.yaml"):
    """Carica la configurazione dal file YAML"""
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        logger.info(f"Configurazione caricata correttamente da {config_path}")
        return config
    except Exception as e:
        logger.error(f"Errore nel caricamento della configurazione: {e}")
        raise

def generate_unique_user_id():
    """Genera un ID utente unico"""
    global user_id_counter
    user_id_counter += 1
    return user_id_counter

def get_nodes_by_type(node_type=None):
    """Ottieni i nodi di un certo tipo"""
    conn = create_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM nodes"
    if node_type:
        query += f" WHERE node_type = '{node_type}'"
    cursor.execute(query)
    nodes = cursor.fetchall()
    cursor.close()
    conn.close()

    nodes_list = []
    for node in nodes:
        node_dict = {
            'node_id': node[0],
            'node_type': node[1],
            'x1': node[2],
            'y1': node[3],
            'z1': node[4],
            'x2': node[5],
            'y2': node[6],
            'z2': node[7],
        }
        nodes_list.append(node_dict)
    return nodes_list

def get_current_position(user_id):
    """Recupera la posizione corrente dell'utente"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT x, y, z, node_id FROM current_position WHERE user_id = %s", (user_id,))
        position = cursor.fetchone()
        cursor.close()
        conn.close()
        if position:
            logger.info(f"Posizione corrente recuperata per l'utente {user_id}: {position}")
        else:
            logger.warning(f"Posizione per l'utente {user_id} non trovata.")
        return position
    except Exception as e:
        logger.error(f"Errore nel recupero della posizione per l'utente {user_id}: {e}")
        return None

def get_current_time_slot(time_slots):
    """Determina lo slot orario in base all'ora attuale"""
    now = datetime.now()
    current_time = now.strftime("%H:%M")  # Ottieni l'ora corrente in formato HH:MM

    # Cerca lo slot corrispondente all'ora attuale
    for slot in time_slots:
        if slot["start"] <= current_time < slot["end"]:
            return slot
    return None

def generate_random_position_within_node(node):
    """Genera una posizione casuale all'interno di un nodo"""
    try:
        # Verifica e correggi l'ordine dei valori per evitare intervalli vuoti o invertiti
        x1, x2 = sorted([node['x1'], node['x2']])
        y1, y2 = sorted([node['y1'], node['y2']])
        z1, z2 = sorted([node['z1'], node['z2']])
        
        x = random.randint(x1, x2)
        y = random.randint(y1, y2)
        z = random.randint(z1, z2)

        logger.info(f"Posizione casuale generata per il nodo {node['node_id']}: ({x}, {y}, {z})")
        return x, y, z
    except Exception as e:
        logger.error(f"Errore nella generazione della posizione casuale per il nodo {node['node_id']}: {e}")
        raise


def send_position_to_position_manager(channel, user_id, x, y, z, node_id, event=None):
    """Invia la posizione al position_manager"""
    try:
        message = {
            "user_id": user_id,
            "x": x,
            "y": y,
            "z": z,
            "node_id": node_id,
            "event": event
        }
        logger.info(f"Inviando posizione: {message}")
        channel.basic_publish(
            exchange='',
            routing_key='position_queue',
            body=json.dumps(message)
        )
        logger.info(f"Inviata posizione per l'utente {user_id} al position_manager: ({x}, {y}, {z})")
    except Exception as e:
        logger.error(f"Errore nell'invio della posizione per l'utente {user_id}: {e}")


def handle_alert(msg):
    """Gestisce il messaggio Alert"""
    if not simulation_active:
        return  # Se la simulazione è stata fermata, non fare nulla

    config = load_config()
    time_slot = get_current_time_slot(config['time_slots'])
    if time_slot is None:
        logger.error("Nessun slot orario trovato per l'ora attuale.")
        return

    logger.info(f"Slot orario trovato: {time_slot['name']}")
    distribution = time_slot['distribution']

    num_users = config['num_users']
    channel, _ = get_rabbitmq_channel()

    for node_type, probability in distribution.items():
        nodes = get_nodes_by_type(node_type)

        if not nodes:
            logger.error(f"Nessun nodo disponibile per il tipo {node_type}. Impossibile simulare il movimento.")
            continue

        for _ in range(int(num_users * probability)):
            node = random.choice(nodes)
            x, y, z = generate_random_position_within_node(node)
            user_id = generate_unique_user_id()
            send_position_to_position_manager(channel, user_id, x, y, z, node['node_id'], event='Alert')

    logger.info("Elaborazione messaggio di allerta completata.")


def handle_evacuation(msg):
    """Gestisce il messaggio Evacuation"""
    if not simulation_active:
        return  # Se la simulazione è stata fermata, non fare nulla

    user_id = msg['user_id']
    evacuation_path = msg['evacuation_path']

    # Recupera la posizione attuale dell'utente
    current_position = get_current_position(user_id)
    if not current_position:
        logger.warning(f"Posizione utente {user_id} non trovata nel DB.")
        return

    x, y, z, node_id = current_position
    channel, _ = get_rabbitmq_channel()

    # Per ogni arco nel percorso di evacuazione
    for arc_id in evacuation_path:
        arc = get_arc_by_id(arc_id)
        if arc:
            final_node_id = arc['final_node']
            final_node = get_nodes_by_type()  # Usa una funzione simile per ottenere i dettagli del final_node
            x, y, z = generate_random_position_within_node(final_node)
            send_position_to_position_manager(channel, user_id, x, y, z, final_node_id)

    logger.info(f"Evacuazione completata per l'utente {user_id}.")


def handle_stop():
    """Gestisce il messaggio Stop"""
    global simulation_active
    logger.info("Ricevuto messaggio Stop. Interrompo la simulazione.")
    simulation_active = False  # Ferma tutte le operazioni


def simulate_user_movement(msg):
    """Simula il movimento degli utenti in base agli eventi ricevuti"""
    msg_type = msg.get('msgType')
    
    if msg_type == 'Alert':
        handle_alert(msg)
    elif msg_type == 'Evacuation':
        handle_evacuation(msg)
    elif msg_type == 'Stop':
        handle_stop()
    else:
        logger.warning(f"Tipo di messaggio non riconosciuto: {msg_type}")
