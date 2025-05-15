import json
import os
import psycopg2
from fastapi import FastAPI, Body, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from MapViewer.app.services.graph_exporter import get_graph_json
from MapViewer.app.services.graph_manager import graph_manager
from MapViewer.app.config.settings import DATABASE_CONFIG, NODE_TYPES
from MapViewer.db.db_connection import create_connection
from MapViewer.db.db_setup import create_tables

app = FastAPI()

IMG_FOLDER = "MapViewer/public/img"
PUBLIC_FOLDER = "MapViewer/public"
JSON_OUTPUT_FOLDER = os.path.join(PUBLIC_FOLDER, "json")

app.mount("/MapViewer/public", StaticFiles(directory=PUBLIC_FOLDER), name="public")

connected_websockets = set()

conn = create_connection()
create_tables()
conn.close()

@app.get("/api/images")
def list_images():
    files = [f for f in os.listdir(IMG_FOLDER) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    return JSONResponse(content={"images": files})

@app.get("/api/map")
def get_map(
    floor: int = Query(...),
    image_filename: str = Query(...),
    image_width: int = Query(...),
    image_height: int = Query(...),
):
    json_path = os.path.join(JSON_OUTPUT_FOLDER, f"floor{floor}.json")
    data = get_graph_json(floor, image_filename, image_width, image_height, output_path=json_path)
    return JSONResponse(content=data)

@app.post("/api/update-node-type")
def update_node_type(data: dict = Body(...)):
    node_id = data.get("node_id")
    node_type = data.get("node_type")
    if not node_id or not node_type:
        return JSONResponse(content={"error": "Missing node_id or node_type"}, status_code=400)

    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("UPDATE nodes SET node_type = %s WHERE node_id = %s", (node_type, node_id))
        conn.commit()
        cur.close()
        conn.close()
        return JSONResponse(content={"message": "Node updated successfully"})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/in-memory-graph")
def get_graph_data(floor: int):
    G = graph_manager.get_graph(floor)
    if not G:
        return JSONResponse(content={"error": "Graph not found"}, status_code=404)

    nodes = [{"id": n, **d} for n, d in G.nodes(data=True)]
    edges = [{"from": u, "to": v, **d} for u, v, d in G.edges(data=True)]
    return JSONResponse(content={"nodes": nodes, "arcs": edges})

@app.get("/api/node-types")
def get_node_types():
    types_list = [
        {"type": key, "display_name": info["display_name"], **({"capacity": info["capacity"]} if "capacity" in info else {})}
        for key, info in NODE_TYPES.items()
    ]
    return JSONResponse(content={"node_types": types_list})

@app.get("/")
async def get_index():
    return FileResponse("MapViewer/public/index.html")

@app.websocket("/ws/map")
async def ws_map(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("action") == "new_node":
                x_px = message["x_px"]
                y_px = message["y_px"]
                floor = message["floor"]
                node_type = message["node_type"]

                new_node = graph_manager.add_node(x_px, y_px, floor, node_type)

                for ws in connected_websockets:
                    await ws.send_text(json.dumps({
                        "action": "node_created",
                        "node": {
                            "node_id": new_node["node_id"],
                            "x": new_node["x"],
                            "y": new_node["y"],
                            "floor_level": new_node["floor_level"],
                            "node_type": new_node["node_type"],
                            "current_occupancy": new_node.get("current_occupancy", 0),
                            "capacity": new_node.get("capacity", 0)
                        }
                    }))

            elif message.get("action") == "create_edge":
                from_id = message["from"]
                to_id = message["to"]
                floor = message["floor"]

                graph_manager.add_edge(from_id, to_id, floor)

                for ws in connected_websockets:
                    await ws.send_text(json.dumps({
                        "action": "edge_created",
                        "edge": {
                            "from": from_id,
                            "to": to_id,
                            "floor": floor
                        }
                    }))

    except WebSocketDisconnect:
        connected_websockets.remove(websocket)
