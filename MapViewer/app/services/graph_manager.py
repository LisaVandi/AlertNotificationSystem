"""
GraphManager is a thread-safe class for managing multiple graphs, each representing a floor level.
It uses NetworkX to handle graph operations and a threading lock to ensure thread safety.
Methods:
    __init__():
        Initializes the GraphManager with an empty dictionary of graphs and a threading lock.
    load_graph(floor_level, nodes, arcs):
        Loads a graph for a specific floor level using the provided nodes and arcs.
        Nodes and arcs are expected to be dictionaries containing their attributes.
    get_graph(floor_level):
        Retrieves the graph associated with the specified floor level.
        Returns None if the floor level does not exist.
    get_all_graphs():
        Returns a copy of all the graphs managed by the GraphManager.
    update_node_occupancy(floor_level, node_id, new_value):
        Updates the 'current_occupancy' attribute of a specific node in the graph
        for the given floor level. Does nothing if the floor level or node does not exist.
Attributes:
    graphs (dict): A dictionary mapping floor levels to their corresponding NetworkX graphs.
    lock (threading.Lock): A lock to ensure thread-safe operations on the graphs.
"""

import networkx as nx
from threading import Lock

class GraphManager:
    def __init__(self):
        self.graphs = {}  # {floor_level: nx.Graph}
        self.lock = Lock()

    def load_graph(self, floor_level, nodes, arcs):
        G = nx.Graph()
        for node in nodes:
            G.add_node(node['id'], **node)

        for arc in arcs:
            G.add_edge(arc['from'], arc['to'], **arc)

        with self.lock:
            self.graphs[floor_level] = G

    def get_graph(self, floor_level):
        with self.lock:
            return self.graphs.get(floor_level)

    def get_all_graphs(self):
        with self.lock:
            return self.graphs.copy()

    def update_node_occupancy(self, floor_level, node_id, new_value):
        with self.lock:
            if floor_level in self.graphs and node_id in self.graphs[floor_level].nodes:
                self.graphs[floor_level].nodes[node_id]['current_occupancy'] = new_value
