UserSimulator Microservice
Overview

The UserSimulator microservice simulates user movement and positioning based on external inputs. It listens to two message queues and generates position updates for virtual users either in response to alerts or predefined evacuation paths.

Features
Listens to Two Queues
1. user_simulator_queue

    If a message with msgType = "Stop" is received:
    → The service stops processing.

    If a message with msgType = "Alert" is received:

        Loads the number and types of users to simulate from a YAML configuration file.

        Retrieves node data from the map_position_db.

        Generates a random position inside each selected node for every user.

        Adds the event field from the original message.

        Sends a message to the position_queue with:
        {
        "user_id": "...",
        "x": ...,
        "y": ...,
        "z": ...,
        "node_id": "...",
        "event": "..."
        }
2. evacuation_paths_queue

    Receives messages like:
    {
    "user_id": "...",
    "evacuation_path": ["arc_id1", "arc_id2", ...]
    }

    For each arc in the path:

        Retrieves the user’s current position from the current_position table in map_position_db.

        Finds the arc in the archs table.

        Gets the final_node of the arc.

        Simulates a new position inside that node.

        Sends an update to the position_queue:
        {
        "user_id": "...",
        "x": ...,
        "y": ...,
        "z": ...,
        "node_id": "..."
        }

Configuration

The service expects a YAML file specifying how many and what types of users to simulate.