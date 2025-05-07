import psycopg2
from psycopg2 import OperationalError

def create_connection():
    try:
        connection = psycopg2.connect(
            dbname="map_position_db", 
            user="postgres", 
            password="postgres", 
            host="localhost", 
            port="5432"
        )
        return connection
    except OperationalError as e:
        print(f"Error: {e}")
        return None
