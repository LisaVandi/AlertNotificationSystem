import os
import json
import psycopg2
from fastapi import FastAPI, Body, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import networkx as nx

from MapViewer.app.services.graph_exporter import get_graph_json
from MapViewer.app.services.graph_manager import graph_manager, GraphManager
from MapViewer.app.config.settings import DATABASE_CONFIG, NODE_TYPES
from MapViewer.db.db_connection import create_connection
from MapViewer.db.db_setup import create_tables

app = FastAPI()

IMG_FOLDER = "MapViewer/public/img"
# PUBLIC_FOLDER = "MapViewer/public"

# app.mount("/MapViewer/public", StaticFiles(directory=PUBLIC_FOLDER), name="public")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_FOLDER = os.path.join(BASE_DIR, "MapViewer", "public")
JSON_OUTPUT_FOLDER = os.path.join(PUBLIC_FOLDER, "json")

app.mount("/static", StaticFiles(directory=PUBLIC_FOLDER), name="static")

conn = create_connection()
create_tables()
conn.close()

def preload_graphs():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT floor_level FROM nodes")
    floors = [row[0] for row in cur.fetchall()]

    if not floors:
        print("Nessun piano trovato nel DB. Grafo in memoria inizializzato vuoto.")
        with graph_manager.lock:
            graph_manager.graphs[0] = nx.Graph()
        cur.close()
        conn.close()
        return

    for floor in floors:
        cur.execute("""
            SELECT node_id, (x1 + x2)/2 AS x, (y1 + y2)/2 AS y, node_type, current_occupancy, capacity
            FROM nodes WHERE floor_level = %s
        """, (floor,))
        nodes = [{"id": r[0], "x": r[1], "y": r[2], "node_type": r[3], "current_occupancy": r[4], "capacity": r[5]} for r in cur.fetchall()]

        cur.execute("""
            SELECT initial_node, final_node, x1, y1, x2, y2, active
            FROM arcs
            WHERE initial_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
            AND final_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
        """, (floor, floor))
        arcs = [{"from": r[0], "to": r[1], "x1": r[2], "y1": r[3], "x2": r[4], "y2": r[5]} for r in cur.fetchall()]

        graph_manager.load_graph(floor, nodes, arcs)
    cur.close()
    conn.close()

graph_manager = GraphManager()
preload_graphs()

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

@app.post("/api/nodes")
def create_node(data: dict = Body(...)):
    x_px = data.get("x_px")
    y_px = data.get("y_px")
    floor = data.get("floor")
    node_type = data.get("node_type")

    if None in [x_px, y_px, floor, node_type]:
        raise HTTPException(status_code=400, detail="Missing node data")

    new_node = graph_manager.add_node(x_px, y_px, floor, node_type)
    return JSONResponse({"node": new_node})

@app.post("/api/edges")
def create_edge(data: dict = Body(...)):
    from_node = data.get("from")
    to_node = data.get("to")
    floor = data.get("floor")

    if None in [from_node, to_node, floor]:
        raise HTTPException(status_code=400, detail="Missing edge data")

    try:
        graph_manager.add_edge(from_node, to_node, floor)
        return {"message": "Edge created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/in-memory-graph")
def get_graph(floor: int):
    G = graph_manager.get_graph(floor)
    if not G:
        return JSONResponse({"nodes": [], "arcs": []})
    
    nodes = [{"id": n, **d} for n, d in G.nodes(data=True)]
    edges = [{"from": u, "to": v, **d} for u, v, d in G.edges(data=True)]
    return JSONResponse({"nodes": nodes, "arcs": edges})

@app.get("/api/node-types")
def get_node_types():
    types_list = [
        {"type": key, "display_name": info["display_name"], **({"capacity": info["capacity"]} if "capacity" in info else {})}
        for key, info in NODE_TYPES.items()
    ]
    return JSONResponse(content={"node_types": types_list})

@app.get("/")
async def get_index():
    index_path = os.path.join(PUBLIC_FOLDER, "index.html")
    return FileResponse(index_path)
