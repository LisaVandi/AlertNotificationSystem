from datetime import datetime, time as dtime
import time
from typing import Dict, List
import random
from collections import defaultdict
from UserSimulator.simulation.user import User
import numpy as np
from UserSimulator.utils.logger import logger

class Simulator:
    def __init__(self, config, nodes, arcs, publisher=None):
        self.config = config
        self.nodes = nodes
        self.arcs = arcs
        self.users = {}
        self.state = "normale"
        self.stop_timer = None
        self.alert_event = None
        self.users_positions = {}
        self.running = False
        self.publisher = publisher

    def initialize_users(self):
        """Initialize users with random positions based on time distribution"""
        logger.info(f"Initializing {self.config.n_users} users")
        
        if self.users:
            logger.info("Users already initialized. Skipping.")
            return
    
        try:
            current_time = datetime.now().time()
            distribution = self.config.get_distribution_for_current_time(current_time)
            
            if not distribution:
                logger.warning("No distribution found - using uniform allocation")
                distribution = {node['node_type']: 1.0 for node in self.nodes}

            node_types = defaultdict(list)
            for node in self.nodes:
                node_types[node['node_type']].append(node)

            for user_id in range(self.config.n_users):
                try:
                    selected_type = random.choices(
                        list(distribution.keys()),
                        weights=list(distribution.values()),
                        k=1
                    )[0]
                    
                    possible_nodes = node_types.get(selected_type, self.nodes)
                    node = random.choice(possible_nodes)
                    
                    user = User(
                        user_id=user_id,
                        node=node,
                        speed_normal=self.config.speed_normal,
                        speed_alert=self.config.speed_alert
                    )
                    
                    self.users[user_id] = user
                    logger.debug(f"User {user_id} created in node {node['node_id']}")

                except Exception as e:
                    logger.error(f"Error creating user {user_id}: {str(e)}")
                    continue

            logger.info(f"Successfully initialized {len(self.users)}/{self.config.n_users} users")

        except Exception as e:
            logger.critical(f" User initialization failed: {str(e)}", exc_info=True)
            raise

    
    def tick(self):
        dt = self.config.simulation_tick
        logger.debug(f"Tick started (dt={dt}s)")

        for user_id, user in self.users.items():
            prev_pos = (user.x, user.y, user.z)
            completed = user.update_position(self.arcs, self.nodes, dt)
            new_pos = (user.x, user.y, user.z)
            
            # Aggiorno sempre il vettore delle posizioni
            self.users_positions[user_id] = user.get_position_message()

            # Pubblico solo se in allerta e se la posizione è cambiata
            if user.state == "allerta" and (prev_pos != new_pos or user.blocked) and self.publisher:
                user.event = self.alert_event
                try:
                    position_msg = user.get_position_message()
                    self.publisher.publish_position(position_msg)
                    logger.debug(f"Published updated position for user {user_id} during alert")
                except Exception as e:
                    logger.error(f"Failed to publish position for user {user_id}: {e}")

        logger.debug(f"Tick completed")


    def handle_alert(self, alert_msg):
        """Handle alert event"""
        if self.state == "allerta":
            logger.warning("Already in alert state - ignoring duplicate alert")
            return

        self.state = "allerta"
        
        self.alert_event = alert_msg.get('info', [{}])[0].get('event', 'unknown')
        logger.warning(f"ALERT TRIGGERED: {self.alert_event}")

        evacuation_paths = alert_msg.get('evacuation_paths', {})  # es: {user_id: [arc_ids]}

        affected = 0
        for user in self.users.values():
            if user.state != "in_attesa_percorso":
                affected += 1
                user.state = "in_attesa_percorso"
                user.speed = 0
                user.event = self.alert_event

            # Se c'è un percorso di evacuazione specifico per l'utente, impostalo
            path = evacuation_paths.get(str(user.user_id), [])
            if path:
                user.set_evacuation_path(path)
                user.state = "allerta"
                user.speed = user.speed_alert
            elif path == [] and evacuation_paths:  
                # Se c'è una mappa ma percorso vuoto, significa utente salvo
                user.mark_as_salvo()
                self.users_positions[user.user_id] = user.get_position_message()
                logger.info(f"After mark_as_salvo, user {user.user_id} state: {user.state}")
            
            
            if self.publisher:
                try:
                    position_msg = {
                        "user_id": user.user_id,
                        "x": user.x,
                        "y": user.y,
                        "z": user.z,
                        "node_id": getattr(user, 'current_node', None),  
                        "event": self.alert_event
                    }
                    self.publisher.publish_position(position_msg)

                    logger.debug(f"Published position for user {user.user_id} due to alert")
                except Exception as e:
                    logger.error(f"Failed to publish position for user {user.user_id}: {e}")

        logger.info(f"Alert applied to {affected} users")


    def handle_stop(self):
        """Handle stop command"""
        if self.state != "allerta":
            logger.warning(f"Unexpected STOP in state '{self.state}'")
            return
            
        self.state = "salvo"
        logger.warning("STOP RECEIVED - Freezing all users")
        
        for user in self.users.values():
            user.state = "salvo"
            user.speed = user.speed_normal
            
        self.stop_timer = datetime.now()

    def _check_stop_resume(self):
        """Check if stop period should end"""
        elapsed = (datetime.now() - self.stop_timer).total_seconds()
        if elapsed > self.config.timeout_after_stop:
            logger.info("Resuming normal operations")
            self.state = "normale"
            for user in self.users.values():
                user.state = "normale"
                user.speed = user.speed_normal
            self.stop_timer = None
    
    def run(self):
        if self.running:
            logger.warning("Simulator.run() already running, skipping.")
            return
        self.running = True

        self.initialize_users()
        logger.info("Simulator run() started.")

        while True:
            self.tick()
            time.sleep(self.config.simulation_tick)
