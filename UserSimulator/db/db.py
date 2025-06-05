import psycopg2
from psycopg2.extras import RealDictCursor
from UserSimulator.utils.logger import logger

class DB:
    def __init__(self, dsn):
        self.dsn = dsn
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(self.dsn)
            logger.info("Connected to DB")
        except Exception as e:
            logger.error(f"DB connection failed: {e}")
            raise

    def get_nodes(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM nodes;")
            nodes = cur.fetchall()
            logger.debug(f"Loaded {len(nodes)} nodes from DB")
            return nodes

    def get_arcs(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM arcs WHERE active = TRUE;")
            arcs = cur.fetchall()
            logger.debug(f"Loaded {len(arcs)} active arcs from DB")
            return arcs

    def get_node_by_id(self, node_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM nodes WHERE node_id = %s;", (node_id,))
            return cur.fetchone()

    def get_arc_by_id(self, arc_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM arcs WHERE arc_id = %s AND active=TRUE;", (arc_id,))
            return cur.fetchone()
