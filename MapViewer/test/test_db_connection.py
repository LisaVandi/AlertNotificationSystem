from MapViewer.app.services.database_handler import DatabaseHandler

def test_connection():
    try:
        db = DatabaseHandler()
        print("Successfully connected to the database!")
        # Fetch some data to verify
        # positions = db.fetch_current_positions()
        # print("User positions:", positions)
        # nodes = db.fetch_map_nodes()
        # print("Nodes:", nodes)
        # arcs = db.fetch_map_arcs()
        # print("Arcs:", arcs)
        db.close()
    except Exception as e:
        print(f"Error connecting to the database: {e}")

if __name__ == "__main__":
    test_connection()