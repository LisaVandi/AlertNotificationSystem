import psycopg2
from typing import List

def get_nodes_by_area(area_type: str) -> List[int]:
    """Recupera tutti i nodi appartenenti a una determinata area dal database."""
    try:
        # Connessione al database
        conn = psycopg2.connect(
            dbname="map_position_db",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()

        # Esegui una query per recuperare i nodi in base al tipo di area
        query = """
            SELECT node_id 
            FROM nodes 
            WHERE node_type = %s
        """
        cursor.execute(query, (area_type,))
        
        # Recupera i risultati
        nodes = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        
        return nodes

    except Exception as e:
        print(f"Error: {e}")
        return []
