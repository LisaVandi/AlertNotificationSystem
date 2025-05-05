from db.db_connection import create_connection

def create_tables():
    conn = create_connection()
    if conn is None:
        print("Failed to connect to the database.")
        return

    cursor = conn.cursor()

    # Table for current positions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS current_position (
            user_id INTEGER PRIMARY KEY,
            x INTEGER,
            y INTEGER,
            z INTEGER
        );
    ''')

    # Table for map nodes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            node_id SERIAL PRIMARY KEY,
            x1 INTEGER,
            x2 INTEGER,
            y1 INTEGER,
            y2 INTEGER,
            z1 INTEGER,
            z2 INTEGER,
            floor_level INTEGER,
            capacity INTEGER,
            node_type VARCHAR(50)
        );
    ''')

    # Table for historical positions per user
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_historical_position (
            user_id INTEGER,
            x INTEGER,
            y INTEGER,
            z INTEGER,
            node_id INTEGER,
            position_type VARCHAR(50),
            danger VARCHAR(50),
            PRIMARY KEY (user_id, node_id),
            FOREIGN KEY (node_id) REFERENCES nodes(node_id)
        );
    ''')


    # Table for map arcs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS arcs (
            arc_id SERIAL PRIMARY KEY,
            flow INTEGER,
            traversal_time INTERVAL, 
            active BOOLEAN,
            x1 INTEGER,
            x2 INTEGER,
            y1 INTEGER,
            y2 INTEGER,
            z1 INTEGER,
            z2 INTEGER,
            capacity INTEGER,
            initial_node INTEGER,
            final_node INTEGER,
            FOREIGN KEY (initial_node) REFERENCES nodes(node_id),
            FOREIGN KEY (final_node) REFERENCES nodes(node_id)
        );
    ''')

    # Table to log changes in the active state of arcs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS arc_status_log (
            log_id SERIAL PRIMARY KEY,
            arc_id INTEGER,
            previous_state BOOLEAN, 
            new_state BOOLEAN,      
            modified_by VARCHAR(100),  
            modification_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (arc_id) REFERENCES arcs(arc_id)
        );
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    print("Database tables created successfully!")

if __name__ == "__main__":
    create_tables()
