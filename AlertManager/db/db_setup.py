"""
CAP Alert Tables Creator for PostgreSQL + PostGIS

This script connects to a PostgreSQL database and creates the main tables 
used to store CAP (Common Alerting Protocol) alerts, including alert metadata, 
associated information blocks, and geographic areas.

The database structure is designed to be compatible with PostGIS for spatial 
data support (e.g., polygons and circles). Indexes are added to optimize query performance.

You can customize the tables by removing or adapting fields according to your project's needs.
"""

from db.db_connection import create_connection 

def create_tables():
    conn = create_connection()
    if conn is None:
        print("❌ Failed to connect to the database.")
        return

    cursor = conn.cursor() 

    # Creating the 'alerts' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,                      -- Unique auto-incremented ID
            identifier VARCHAR(255) NOT NULL UNIQUE,    -- Unique identifier assigned by the sender
            sender VARCHAR(255) NOT NULL,               -- Alert originator
            sent TIMESTAMP NOT NULL,                    -- Alert creation timestamp
            status VARCHAR(50) NOT NULL,                -- Handling status (actual, exercise, system, test, draft)
            msgType VARCHAR(50) NOT NULL,               -- Message type (alert, update, cancel, ack, error)
            scope VARCHAR(50) NOT NULL                  -- Distribution scope (public, restricted, private)
        );
    ''')

    # Creating the 'info' table (additional information block for the alert)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS info (
            id SERIAL PRIMARY KEY,                                      -- Unique auto-incremented ID
            alert_id INT REFERENCES alerts(id) ON DELETE CASCADE,       -- Reference to the main alert
                
            category VARCHAR(50),         -- Event category (met, safety, security, rescue, fire, health, env, transport, infra, CBRNE, other)
            event VARCHAR(255),           -- Event type
            urgency VARCHAR(50),          -- Urgency level
            severity VARCHAR(50),         -- Severity level
            certainty VARCHAR(50),        -- Certainty level
            
            language VARCHAR(50),         -- Language (default: en-US)
            responseType VARCHAR(50),     -- Recommended response type
            description TEXT,             -- Detailed alert description
            instruction TEXT              -- Recommended actions
        );
    ''')

    # Creating the 'areas' table (geographical areas associated with the alert)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS areas (
            id SERIAL PRIMARY KEY,                                      -- Unique auto-incremented ID
            alert_id INT REFERENCES alerts(id) ON DELETE CASCADE,       -- Reference to the main alert
                
            areaDesc TEXT,                                              -- Area description  
            geometry_type VARCHAR(50),                                  -- Type of geometry (polygon or area)
            geom GEOMETRY,                                              -- Geometry of the area 
            altitude FLOAT                                              -- Altitude of the affected area (meters)
        );
    ''')

    # Creating indexes to optimize queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_info_alert_id ON info(alert_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_areas_alert_id ON areas(alert_id);")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    create_tables()
