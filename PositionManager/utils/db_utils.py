# === utils/db_utils.py ===

from utils.db import get_connection

def update_current_position(user_pos):
    conn = get_connection()
    cur = conn.cursor()

    # Verifica se l'utente esiste già nella tabella current_position
    cur.execute('''
        SELECT 1 FROM current_position WHERE user_id = %s
    ''', (user_pos['user_id'],))
    exists = cur.fetchone()

    if exists:
        # Se l'utente esiste, eseguiamo un aggiornamento
        cur.execute('''
            UPDATE current_position
            SET x = %s, y = %s, z = %s, node_id = %s, danger = %s
            WHERE user_id = %s
        ''', (user_pos['x'], user_pos['y'], user_pos['z'], user_pos['node_id'], user_pos['danger'], user_pos['user_id']))
    else:
        # Se l'utente non esiste, eseguiamo un inserimento
        cur.execute('''
            INSERT INTO current_position (user_id, x, y, z, node_id, danger)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (user_pos['user_id'], user_pos['x'], user_pos['y'], user_pos['z'], user_pos['node_id'], user_pos['danger']))

    conn.commit()
    cur.close()
    conn.close()


def insert_historical_position(user_pos):
    conn = get_connection()
    cur = conn.cursor()

    # Verifica se l'utente ha già una posizione storica per il nodo
    cur.execute('''
        SELECT 1 FROM user_historical_position
        WHERE user_id = %s AND node_id = %s
    ''', (user_pos['user_id'], user_pos['node_id']))
    exists = cur.fetchone()

    if not exists:
        # Se non esiste, eseguiamo un inserimento
        cur.execute('''
            INSERT INTO user_historical_position (user_id, x, y, z, node_id, danger)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (user_pos['user_id'], user_pos['x'], user_pos['y'], user_pos['z'], user_pos['node_id'], user_pos['danger']))

    conn.commit()
    cur.close()
    conn.close()


def get_evacuation_path(node_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT evacuation_path FROM nodes WHERE node_id = %s", (node_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else []

def get_floor_from_node(node_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT floor_level FROM nodes WHERE node_id = %s", (node_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None
