from MapViewer.db.db_connection import create_connection

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
            node_type VARCHAR(50), 
            current_occupancy INT DEFAULT 0
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
    
    # Logging function for arc state changes
    cursor.execute('''
        CREATE OR REPLACE FUNCTION log_arc_status_change() 
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.active <> OLD.active THEN
                INSERT INTO arc_status_log (arc_id, previous_state, new_state, modified_by)
                VALUES (NEW.arc_id, OLD.active, NEW.active, 'system');
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')

    # Trigger to call the function after updates to arcs
    cursor.execute('''
        DROP TRIGGER IF EXISTS trigger_arc_status_change ON arcs;
        CREATE TRIGGER trigger_arc_status_change
        AFTER UPDATE OF active ON arcs
        FOR EACH ROW
        EXECUTE FUNCTION log_arc_status_change();
    ''')

    
    # Table to keep track of how many updates have occurred
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS update_counter (
            id INTEGER PRIMARY KEY DEFAULT 1,
            count INTEGER DEFAULT 0
        );
    ''')

    # Ensure exactly one row exists in update_counter
    cursor.execute("INSERT INTO update_counter (id, count) VALUES (1, 0) ON CONFLICT (id) DO NOTHING;")

    # Drop existing trigger and function if they exist
    cursor.execute("DROP TRIGGER IF EXISTS trg_notify_position_update ON current_position;")
    cursor.execute("DROP FUNCTION IF EXISTS notify_position_update();")

    # Create the trigger function
    cursor.execute('''
        CREATE OR REPLACE FUNCTION notify_position_update()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Increment the counter
            UPDATE update_counter SET count = count + 1 WHERE id = 1;

            -- Only send NOTIFY every 100 updates
            IF (SELECT count FROM update_counter WHERE id = 1) % 100 = 0 THEN
                PERFORM pg_notify('position_update', 'Threshold reached');
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')

    # Create the trigger on INSERT or UPDATE of current_position
    cursor.execute('''
        CREATE TRIGGER trg_notify_position_update
        AFTER INSERT OR UPDATE ON current_position
        FOR EACH ROW
        EXECUTE FUNCTION notify_position_update();
    ''')
    
     # Create function to update node occupancy
    cursor.execute('''
        CREATE OR REPLACE FUNCTION update_node_occupancy()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Reset all current occupancies
            UPDATE nodes SET current_occupancy = 0;

            -- Count how many users are inside each node and update
            UPDATE nodes
            SET current_occupancy = sub.occupancy
            FROM (
                SELECT node_id, COUNT(*) AS occupancy
                FROM current_position cp
                JOIN nodes n ON cp.x BETWEEN n.x1 AND n.x2 AND cp.y BETWEEN n.y1 AND n.y2 AND cp.z BETWEEN n.z1 AND n.z2
                GROUP BY node_id
            ) AS sub
            WHERE nodes.node_id = sub.node_id;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    ''')

    # Trigger to update node occupancy on change to current_position
    cursor.execute('''
        DROP TRIGGER IF EXISTS trg_update_node_occupancy ON current_position;
        CREATE TRIGGER trg_update_node_occupancy
        AFTER INSERT OR UPDATE OR DELETE ON current_position
        FOR EACH STATEMENT
        EXECUTE FUNCTION update_node_occupancy();
    ''')    

    conn.commit()
    cursor.close()
    conn.close()
    print("Database tables created successfully!")

if __name__ == "__main__":
    create_tables()
