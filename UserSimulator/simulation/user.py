import numpy as np
from UserSimulator.utils.logger import logger

class User:
    def __init__(self, user_id, node, speed_normal, speed_alert):
        """
        Initialize the User.

        Args:
            user_id (int): Unique user identifier
            node (dict): The current node where the user is located (dictionary with node info)
            speed_normal (float): Speed in normal state
            speed_alert (float): Speed in alert state
        """
        self.waiting_for_path = False
        self.path_wait_timer = 0
        self.MAX_WAIT_TIME = 10
        
        self.user_id = user_id
        self.current_node = node['node_id']  # Node ID where user currently is
        # Start position randomly inside the node boundaries
        self.x = np.random.uniform(node['x1'], node['x2'])
        self.y = np.random.uniform(node['y1'], node['y2'])
        self.z = np.random.uniform(node['z1'], node['z2'])

        self.state = "normale"  # normale, allerta, salvo
        self.speed_normal = speed_normal
        self.speed_alert = speed_alert
        self.speed = speed_normal

        self.event = None  # Current event string if in alert

        self.evacuation_path = []  # List of arc_ids to traverse
        self.moving_along_arc = False  # Are we currently moving along an arc?
        self.arc_progress = 0.0  # Progress along the current arc [0,1]

        logger.info(
            f"[INIT] User {self.user_id} initialized in node {self.current_node} at pos=({self.x:.2f}, {self.y:.2f}, {self.z:.2f}), state={self.state}"
        )

    def get_position_message(self):
        """
        Restituisce il messaggio da pubblicare con la posizione e lo stato.
        Il campo 'event' è sempre quello dell'allerta ricevuta (self.event).
        """
        return {
            "user_id": self.user_id,
            "x": int(round(self.x)),
            "y": int(round(self.y)),
            "z": int(round(self.z)),
            "node_id": self.current_node,
            "event": self.event  # <-- sempre lo stesso valore impostato dall'allerta
        }

    def update_position(self, arcs, nodes, dt):
        """
        Update user's position based on current state.

        Args:
            arcs (list): List of arcs in the environment
            nodes (list): List of nodes in the environment
            dt (float): Time delta since last update (seconds)
        """
        logger.info(f"User {self.user_id} state={self.state} updating position")

        if self.state == "allerta":
            if self.speed == 0:
                # User fermo perché nessun percorso assegnato
                logger.debug(f"User {self.user_id} in ALERT but speed=0, not moving")
                return
            # muovi lungo percorso di evacuazione
            self._move_along_path(arcs, dt)
        elif self.state == "salvo":
            # fermo in posizione attuale (speed=0)
            logger.debug(f"User {self.user_id} in SALVO, not moving")
            return
        else:
            # stato normale, movimento casuale o normale
            self._move_free(arcs, nodes, dt)
        

    def _move_free(self, arcs, nodes, dt):
        """
        Move randomly in 3D space with realistic step based on speed and dt.
        If movement causes change of node, check arc validity.
        """
        distance = self.speed * dt  # distanza percorribile in dt

        # Direzione casuale nel 3D
        direction = np.random.normal(size=3)
        direction /= np.linalg.norm(direction)

        dx, dy, dz = direction * distance
        new_x = self.x + dx
        new_y = self.y + dy
        new_z = self.z + dz

        # Trova il nodo in cui finirebbe il nuovo punto
        target_node = self._find_node_containing_point(new_x, new_y, new_z, nodes)

        if target_node:
            # Movimento interno allo stesso nodo o spostamento valido
            if target_node['node_id'] == self.current_node or \
            self._is_connected(self.current_node, target_node['node_id'], arcs):
                logger.info(f"User {self.user_id} moved from node {self.current_node} to node {target_node['node_id']}")
                self.current_node = target_node['node_id']
                self.x, self.y, self.z = new_x, new_y, new_z
            else:
                logger.info(f"User {self.user_id} blocked: no arc from {self.current_node} to {target_node['node_id']}")
        else:
            logger.debug(f"User {self.user_id} move out of bounds prevented")

    def _find_node_containing_point(self, x, y, z, nodes):
        for node in nodes:
            if node['x1'] <= x <= node['x2'] and \
            node['y1'] <= y <= node['y2'] and \
            node['z1'] <= z <= node['z2']:
                return node
        return None

    def _is_connected(self, node_a, node_b, arcs):
        for arc in arcs:
            if (arc['initial_node'] == node_a and arc['final_node'] == node_b) or \
            (arc['initial_node'] == node_b and arc['final_node'] == node_a):
                return True
        return False

    def _move_along_path(self, arcs, dt):
        """
        Move user along the evacuation path arcs progressively.

        Args:
            arcs (list): list of all arcs (dict with arc info)
            dt (float): time delta (seconds)
        """
        
        if not self.evacuation_path:
            # NON chiamare clear_evacuation_path per timeout
            # Mantieni l'utente in stato 'allerta' finché non arriva un percorso valido
            logger.info(f"User {self.user_id} has no evacuation path but remains in ALERT state")
            return

        
        # Se arriva qui, c'è un percorso da seguire
        self.waiting_for_path = False
        self.path_wait_timer = 0
    
    # ... (resto del metodo esistente)

        current_arc_id = self.evacuation_path[0]
        arc = next((a for a in arcs if a['arc_id'] == current_arc_id), None)

        if arc is None:
            logger.warning(f"User {self.user_id}: arc {current_arc_id} not found in arcs list")
            # Remove the missing arc and try next
            self.evacuation_path.pop(0)
            self.moving_along_arc = False
            self.arc_progress = 0.0
            return

        # If not currently moving along an arc, initialize progress
        if not self.moving_along_arc:
            self.moving_along_arc = True
            self.arc_progress = 0.0
            logger.info(f"User {self.user_id} started moving along arc {current_arc_id}")

        # Determine direction based on current node and arc nodes
        if self.current_node == arc['initial_node']:
            start_pos = np.array([arc['x1'], arc['y1'], arc['z1']])
            end_pos = np.array([arc['x2'], arc['y2'], arc['z2']])
            next_node = arc['final_node']
        elif self.current_node == arc['final_node']:
            # Reverse direction on the same arc
            start_pos = np.array([arc['x2'], arc['y2'], arc['z2']])
            end_pos = np.array([arc['x1'], arc['y1'], arc['z1']])
            next_node = arc['initial_node']
        else:
            logger.warning(f"User {self.user_id} current node {self.current_node} not connected to arc {current_arc_id}")
            # Drop this arc and reset movement
            self.evacuation_path.pop(0)
            self.moving_along_arc = False
            self.arc_progress = 0.0
            return

        arc_length = np.linalg.norm(end_pos - start_pos)
        if arc_length == 0:
            logger.warning(f"User {self.user_id} arc {current_arc_id} has zero length")
            self.evacuation_path.pop(0)
            self.moving_along_arc = False
            self.arc_progress = 0.0
            return

        # Increment progress along arc based on speed and dt
        self.arc_progress += (self.speed * dt) / arc_length

        if self.arc_progress >= 1.0:
            # User reached the end of the arc (the next node)
            self.current_node = next_node
            self.x, self.y, self.z = end_pos
            logger.info(f"User {self.user_id} reached node {self.current_node} via arc {current_arc_id}")

            # Remove the arc from the evacuation path
            self.evacuation_path.pop(0)

            # Reset movement state on arc
            self.moving_along_arc = False
            self.arc_progress = 0.0

            # If no more arcs, clear path and return to normal state
            if not self.evacuation_path:
                self.clear_evacuation_path()
        else:
            # User is still moving along the arc, interpolate position
            pos = start_pos + self.arc_progress * (end_pos - start_pos)
            self.x, self.y, self.z = pos
            logger.info(f"User {self.user_id} moved along arc {current_arc_id} to pos ({self.x:.2f}, {self.y:.2f}, {self.z:.2f})")

    def set_evacuation_path(self, arc_list):
        """
        Set a new evacuation path for the user.
        If arc_list is empty, clear the evacuation path and return to normal.
        Otherwise, update the path and set state to alert.
        """
        if not arc_list:
            # Se la nuova lista è vuota significa fine evacuazione, torna normale
            self.clear_evacuation_path()
            self.speed = 0
            self.state = "allerta"
            logger.info(f"User {self.user_id} received empty path - cleared evacuation and returned to NORMAL")
            return
        
        # Altrimenti aggiorna il percorso (anche se c'era un percorso precedente)
        self.evacuation_path = arc_list
        self.moving_along_arc = False
        self.arc_progress = 0.0
        self.state = "allerta"
        self.speed = self.speed_alert
        self.event = self.event or "evacuazione_in_corso"  # mantiene eventuale evento di allerta
        self.waiting_for_path = False
        self.path_wait_timer = 0
        logger.info(f"User {self.user_id} updated evacuation path with {len(arc_list)} arcs and remains in ALERT")


    def clear_evacuation_path(self):
        """
        Clear the evacuation path and return to normal state.
        """
        self.evacuation_path = []
        self.moving_along_arc = False
        self.arc_progress = 0.0
        self.state = "normale"
        self.speed = self.speed_normal
        self.event = None
        self.waiting_for_path = False
        self.path_wait_timer = 0
        logger.info(f"User {self.user_id} cleared evacuation path and returned to NORMAL state")