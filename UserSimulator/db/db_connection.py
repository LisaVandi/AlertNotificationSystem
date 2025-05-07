import psycopg2
from typing import List

def get_nodes_by_area(area_type: str):
    """Recupera tutti i nodi appartenenti a una determinata area dal database."""
    try:
        conn = psycopg2.connect(
            dbname="map_position_db",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()

        # Query per recuperare i dettagli dei nodi associati all'area
        query = """
            SELECT node_id, x1, x2, y1, y2, z1, z2
            FROM nodes
            WHERE node_type = %s
        """
        cursor.execute(query, (area_type,))
        
        # Recupera i nodi con tutte le informazioni necessarie per simulare la posizione
        nodes = [{"node_id": row[0], "x1": row[1], "x2": row[2], "y1": row[3], "y2": row[4], "z1": row[5], "z2": row[6]} for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return nodes

    except Exception as e:
        print(f"Error: {e}")
        return []

