import psycopg2
import logging

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection configuration
DB_NAME = "alert_db"  # Your database name
DB_USER = "alert_user"  # Database user name
DB_PASSWORD = "Passworduser"  # Database password
DB_HOST = "localhost"  # Server address
DB_PORT = "5432"  # Default PostgreSQL port

# Function to create the database connection
def create_connection():
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logger.info("✅ Database connection successful!")
        return conn
    except Exception as e:
        logger.error(f"❌ Connection error: {e}")
        return None

# Test function to connect to the database and check PostGIS
def test_postgis():
    conn = create_connection()
    if conn is None:
        print("❌ Database connection failed.")
        return

    # Create a cursor
    cursor = conn.cursor()

    # Check if PostGIS is enabled
    try:
        cursor.execute("SELECT PostGIS_version();")
        postgis_version = cursor.fetchone()
        print(f"PostGIS is active! Version: {postgis_version[0]}")
    except Exception as e:
        print(f"❌ Error while checking PostGIS: {e}")
    
    # Close the connection
    cursor.close()
    conn.close()

if __name__ == "__main__":
    test_postgis()
