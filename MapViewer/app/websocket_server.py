import asyncio
import asyncpg
import websockets
import json
import psycopg2
from MapViewer.app.config.settings import DATABASE_CONFIG
from MapViewer.app.services.graph_manager import graph_manager

connected_clients = set()

async def websocket_handler(websocket):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                print(f"[DEBUG] Messaggio WebSocket ricevuto: {data}")

                if data.get("action") == "new_node":
                    x_px = data["x_px"]
                    y_px = data["y_px"]
                    floor = data["floor"]
                    node_type = data["node_type"]

                    new_node = graph_manager.add_node(x_px, y_px, floor, node_type)

                    await broadcast({
                        "action": "node_created",
                        "node": new_node
                    })

                elif data.get("action") == "create_edge":
                    print(f"[DEBUG] create_edge ricevuto: {data}")
                    from_id = data["from"]
                    to_id = data["to"]
                    floor = data["floor"]

                    graph_manager.add_edge(from_id, to_id, floor)

                    await broadcast({
                        "action": "edge_created",
                        "edge": {
                            "from": from_id,
                            "to": to_id,
                            "floor": floor
                        }
                    })

            except Exception as e:
                print(f"[WS ERROR] {e}")
    finally:
        connected_clients.remove(websocket)

async def broadcast(message: dict):
    to_remove = set()
    for client in connected_clients:
        try:
            await client.send(json.dumps(message))
        except Exception:
            to_remove.add(client)
    connected_clients.difference_update(to_remove)

async def send_refresh_signal():
    print("[NOTIFY] PostgreSQL sent update → Refreshing clients")
    await broadcast("refresh")

async def listen_pg():
    conn = await asyncpg.connect(
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
        database=DATABASE_CONFIG["database"],
        host=DATABASE_CONFIG["host"],
        port=DATABASE_CONFIG["port"]
    )
    await conn.add_listener('position_update', lambda *args: asyncio.create_task(send_refresh_signal()))
    await conn.add_listener('node_update', lambda *args: asyncio.create_task(send_refresh_signal()))
    await conn.add_listener('arc_update', lambda *args: asyncio.create_task(send_refresh_signal()))
    print("[WS] Subscribed to PostgreSQL channels: position_update, node_update, arc_update")

    while True:
        await asyncio.sleep(3600)

def preload_graphs_from_db():
    print("[INIT] Caricamento grafi dal DB...")
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT floor_level FROM nodes")
    floors = [row[0] for row in cur.fetchall()]

    for floor in floors:
        cur.execute("""
            SELECT node_id, (x1 + x2)/2 AS x, (y1 + y2)/2 AS y, node_type, current_occupancy, capacity
            FROM nodes
            WHERE floor_level = %s
        """, (floor,))
        nodes = [{"id": r[0], "x": r[1], "y": r[2], "node_type": r[3], "current_occupancy": r[4], "capacity": r[5]} for r in cur.fetchall()]

        cur.execute("""
            SELECT initial_node, final_node, x1, y1, x2, y2
            FROM arcs
            WHERE initial_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
            AND final_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
        """, (floor, floor))
        arcs = [{"from": r[0], "to": r[1], "x1": r[2], "y1": r[3], "x2": r[4], "y2": r[5]} for r in cur.fetchall()]

        graph_manager.load_graph(floor, nodes, arcs)
        print(f"[INIT] Piano {floor} caricato con {len(nodes)} nodi e {len(arcs)} archi")

    cur.close()
    conn.close()

async def main():
    preload_graphs_from_db()
    print("[WS] WebSocket server listening on ws://localhost:8765")
    await asyncio.gather(
        websockets.serve(websocket_handler, "localhost", 8765),
        listen_pg()
    )

if __name__ == "__main__":
    asyncio.run(main())
