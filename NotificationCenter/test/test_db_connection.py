from NotificationCenter.app.services.database_handler import DatabaseHandler

def test_connection():
    try:
        db = DatabaseHandler()
        print("Successfully connected to the database!")
        # Fetch some data to verify
        db.close()
    except Exception as e:
        print(f"Error connecting to the database: {e}")

if __name__ == "__main__":
    test_connection()