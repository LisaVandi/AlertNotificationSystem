-- Table for current positions
CREATE TABLE current_position (
    user_id INTEGER PRIMARY KEY,
    x INTEGER,
    y INTEGER,
    z INTEGER
);

-- Table for historical positions per user
CREATE TABLE user_historical_position (
    user_id INTEGER,
    x INTEGER, -- effective x position
    y INTEGER, -- effective y position
    z INTEGER, -- effective z position
    node_id INTEGER, -- node_id
    position_type VARCHAR(50),
    danger VARCHAR(50), -- danger level for a specific area
    PRIMARY KEY (user_id, node_id),
    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
);

-- Table for map nodes
CREATE TABLE nodes (
    node_id SERIAL PRIMARY KEY, -- node_id auto-incrementa ad ogni inserimento
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

-- Table for map arcs
CREATE TABLE arcs (
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

-- Table to log changes in the 'active' state of arcs
CREATE TABLE arc_status_log (
    log_id SERIAL PRIMARY KEY,
    arc_id INTEGER,
    previous_state BOOLEAN, 
    new_state BOOLEAN,      
    modified_by VARCHAR(100),  
    modification_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (arc_id) REFERENCES arcs(arc_id) 
);
