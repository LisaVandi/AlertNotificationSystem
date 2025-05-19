import random
import pika
import json
from MapViewer.db.db_connection import create_connection  # Import the database connection utility
from UserSimulator.rabbitmq.rabbitmq_manager import get_rabbitmq_channel  # Import RabbitMQ connection manager
from utils.logger import logger  # Import the logger for logging events and errors
from datetime import datetime
import yaml

# Global variables to track the last user_id and the simulation state
user_id_counter = 0  # Start with a base ID
simulation_active = True  # Global flag to control the simulation state

def load_config(config_path="UserSimulator/config/config.yaml"):
    """Loads the configuration from the YAML file"""
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)  # Read YAML configuration
        logger.info(f"Configuration successfully loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise

def generate_unique_user_id():
    """Generates a unique user ID"""
    global user_id_counter
    user_id_counter += 1  # Increment the counter for each new user
    return user_id_counter

def get_nodes_by_type(node_type=None):
    """Retrieves nodes of a specific type from the database"""
    conn = create_connection()  # Establish database connection
    cursor = conn.cursor()
    query = "SELECT * FROM nodes"
    if node_type:
        query += f" WHERE node_type = '{node_type}'"  # Filter nodes by type if specified
    cursor.execute(query)
    nodes = cursor.fetchall()  # Fetch all nodes
    cursor.close()
    conn.close()

    nodes_list = []
    for node in nodes:
        node_dict = {
            'node_id': node[0],  # Node ID
            'node_type': node[1],  # Node type (e.g., classroom, corridor, etc.)
            'x1': node[2],  # Coordinates of the first corner
            'y1': node[3],
            'z1': node[4],
            'x2': node[5],  # Coordinates of the second corner
            'y2': node[6],
            'z2': node[7],
        }
        nodes_list.append(node_dict)
    return nodes_list

def get_current_position(user_id):
    """Fetches the current position of the user from the database"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT x, y, z, node_id FROM current_position WHERE user_id = %s", (user_id,))
        position = cursor.fetchone()  # Fetch the user's position
        cursor.close()
        conn.close()
        if position:
            logger.info(f"Current position retrieved for user {user_id}: {position}")
        else:
            logger.warning(f"Position for user {user_id} not found.")
        return position
    except Exception as e:
        logger.error(f"Error retrieving position for user {user_id}: {e}")
        return None

def get_current_time_slot(time_slots):
    """Determines the current time slot based on the current time"""
    now = datetime.now()
    current_time = now.strftime("%H:%M")  # Get the current time in HH:MM format

    # Search for the corresponding time slot based on the current time
    for slot in time_slots:
        if slot["start"] <= current_time < slot["end"]:
            return slot
    return None

def generate_random_position_within_node(node):
    """Generates a random position within a node's boundaries"""
    try:
        # Ensure the coordinates are in the correct order to avoid empty or inverted ranges
        x1, x2 = sorted([node['x1'], node['x2']])
        y1, y2 = sorted([node['y1'], node['y2']])
        z1, z2 = sorted([node['z1'], node['z2']])
        
        x = random.randint(x1, x2)  # Generate random position within the node
        y = random.randint(y1, y2)
        z = random.randint(z1, z2)

        logger.info(f"Random position generated for node {node['node_id']}: ({x}, {y}, {z})")
        return x, y, z
    except Exception as e:
        logger.error(f"Error generating random position for node {node['node_id']}: {e}")
        raise


def send_position_to_position_manager(channel, user_id, x, y, z, node_id, event=None):
    """Sends the generated position to the position manager via RabbitMQ"""
    try:
        message = {
            "user_id": user_id,  # The user's unique ID
            "x": x,  # The x-coordinate of the position
            "y": y,  # The y-coordinate of the position
            "z": z,  # The z-coordinate of the position
            "node_id": node_id,  # The ID of the node the user is in
            "event": event  # Event information (if available)
        }
        logger.info(f"Sending position: {message}")
        channel.basic_publish(
            exchange='',
            routing_key='position_queue',  # Routing the message to the position queue
            body=json.dumps(message)
        )
        logger.info(f"Position for user {user_id} sent to position_manager: ({x}, {y}, {z})")
    except Exception as e:
        logger.error(f"Error sending position for user {user_id}: {e}")


def handle_alert(msg):
    """Handles the 'Alert' message type"""
    if not simulation_active:
        return  # Do nothing if simulation is stopped

    config = load_config()  # Load the configuration
    time_slot = get_current_time_slot(config['time_slots'])  # Determine the current time slot
    if time_slot is None:
        logger.error("No time slot found for the current time.")
        return

    logger.info(f"Time slot found: {time_slot['name']}")
    distribution = time_slot['distribution']  # Distribution of users across nodes for this time slot

    num_users = config['num_users']  # Total number of users to simulate
    channel, _ = get_rabbitmq_channel()  # Get RabbitMQ channel

    # Extract each event from the "info" list in the message
    for alert_info in msg.get("info", []):
        event = alert_info.get("event", "Unknown")
        logger.info(f"Processing event of type '{event}'")

    for node_type, probability in distribution.items():
        nodes = get_nodes_by_type(node_type)  # Retrieve nodes by type (e.g., classrooms, corridors)

        if not nodes:
            logger.error(f"No nodes available for node type {node_type}. Cannot simulate movement.")
            continue

        for _ in range(int(num_users * probability)):  # Simulate users based on the probability distribution
            node = random.choice(nodes)
            x, y, z = generate_random_position_within_node(node)
            user_id = generate_unique_user_id()  # Generate a unique user ID
            send_position_to_position_manager(channel, user_id, x, y, z, node['node_id'], event=event)  # Send user position

    logger.info("Alert message processing completed.")


def handle_evacuation(msg):
    """Handles the 'Evacuation' message type"""
    if not simulation_active:
        return  # Do nothing if simulation is stopped

    user_id = msg['user_id']  # Get the user ID
    evacuation_path = msg['evacuation_path']  # Get the evacuation path

    # Retrieve the current position of the user
    current_position = get_current_position(user_id)
    if not current_position:
        logger.warning(f"User {user_id} position not found in the database.")
        return

    x, y, z, node_id = current_position
    channel, _ = get_rabbitmq_channel()  # Get RabbitMQ channel

    # For each arc in the evacuation path
    for arc_id in evacuation_path:
        arc = get_arc_by_id(arc_id)  # Get arc details by ID
        if arc:
            final_node_id = arc['final_node']  # Get the final node in the path
            final_node = get_nodes_by_type()  # Retrieve final node details
            x, y, z = generate_random_position_within_node(final_node)  # Generate new random position
            send_position_to_position_manager(channel, user_id, x, y, z, final_node_id)  # Send the new position

    logger.info(f"Evacuation completed for user {user_id}.")


def handle_stop():
    """Handles the 'Stop' message type"""
    global simulation_active
    logger.info("Received Stop message. Stopping the simulation.")
    simulation_active = False  # Stop the simulation

def simulate_user_movement(msg):
    """Simulates user movement based on the received event message"""
    msg_type = msg.get('msgType')  # Get the type of message (Alert, Evacuation, Stop)
    
    if msg_type == 'Alert':
        handle_alert(msg)  # Handle the alert event
    elif msg_type == 'Evacuation':
        handle_evacuation(msg)  # Handle the evacuation event
    elif msg_type == 'Stop':
        handle_stop()  # Stop the simulation if the stop event is received
    else:
        logger.warning(f"Unrecognized message type: {msg_type}")  # Log a warning if the message type is unknown
