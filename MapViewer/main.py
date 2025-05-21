import json
import os
import psycopg2
import networkx as nx
import re
import asyncio

from fastapi import FastAPI, Body, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from datetime import datetime

from MapViewer.app.services.graph_exporter import get_graph_json
from MapViewer.app.services.graph_manager import graph_manager
from MapViewer.app.config.settings import DATABASE_CONFIG, NODE_TYPES
from MapViewer.db.db_connection import create_connection
from MapViewer.db.db_setup import create_tables

async def clear_positions_on_shutdown():
    loop = asyncio.get_event_loop()

    def db_cleanup():
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        try:
            cur.execute("SELECT user_id, x, y, z, node_id, danger FROM user_historical_position")
            rows = cur.fetchall()
            data = [
                {"user_id": r[0], "x": r[1], "y": r[2], "z": r[3], "node_id": r[4], "danger": r[5]}
                for r in rows
            ]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = os.path.join(JSON_OUTPUT_FOLDER, f"user_historical_position_{ts}.json")
            os.makedirs(os.path.dirname(json_path), exist_ok=True)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            cur.execute("DELETE FROM current_position;")
            cur.execute("DELETE FROM user_historical_position;")
            conn.commit()
        except Exception as e:
            print("Errore durante la pulizia:", e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()

    await loop.run_in_executor(None, db_cleanup)

# Definisci lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Codice da eseguire all'avvio (opzionale)
    yield
    # Codice da eseguire alla terminazione (shutdown)
    await clear_positions_on_shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            
    allow_credentials=True,
    allow_methods=["*"],            
    allow_headers=["*"],            
)

IMG_FOLDER = "MapViewer/public/img"
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
    try:
        with graph_manager.lock:
            graph_manager.graphs.clear()
            print("Grafo in memoria svuotato.")

        cur.execute("SELECT DISTINCT floor_level FROM nodes")
        floors = [row[0] for row in cur.fetchall()]

        for floor in floors:
            cur.execute("""
                SELECT node_id, x1, x2, y1, y2, node_type, current_occupancy, capacity, floor_level
                FROM nodes WHERE floor_level = %s
            """, (floor,))
            nodes_db = cur.fetchall()
            
            nodes = []
            for r in nodes_db:
                node_id, x1, x2, y1, y2, node_type, occ, cap, floor_level = r
                x_center = (x1 + x2) / 2
                y_center = (y1 + y2) / 2
                nodes.append({
                    "id": node_id,
                    "x": x_center,
                    "y": y_center,
                    "node_type": node_type,
                    "current_occupancy": occ,
                    "capacity": cap,
                    "floor_level": floor_level
                })

            cur.execute("""
                SELECT initial_node, final_node, x1, y1, x2, y2, active
                FROM arcs
                WHERE initial_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
                AND final_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
            """, (floor, floor))
            arc_rows = cur.fetchall()
            print(f"Floor {floor}: caricati {len(nodes)} nodi e {len(arc_rows)} archi dal DB")

            arcs = []
            for r in arc_rows:
                initial_node, final_node, x1, y1, x2, y2, active = r
                arcs.append({
                    "initial_node": initial_node,
                    "final_node": final_node,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "active": active
                })

            graph_manager.load_graph(floor, nodes, arcs)
    finally:
        cur.close()
        conn.close()

preload_graphs()

@app.get("/api/images")
def list_images():
    files = [f for f in os.listdir(IMG_FOLDER) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    def floor_num(fname):
        m = re.search(r"floor(\d+)", fname, re.I)
        return int(m.group(1)) if m else 0          

    files.sort(key=floor_num)
    
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
    image_height = data.get("image_height")

    print(f"Received node creation data: x_px={x_px}, y_px={y_px}, floor={floor}, node_type={node_type}, image_height={image_height}")

    if None in [x_px, y_px, floor, node_type, image_height]:
        raise HTTPException(status_code=400, detail="Missing node data")

    new_node = graph_manager.add_node(x_px, y_px, floor, node_type, image_height)
    return JSONResponse({"node": new_node})

@app.post("/api/edges")
def create_edge(data: dict = Body(...)):
    from_node = data.get("initial_node")
    to_node = data.get("final_node")
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
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
    }
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        
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
        arcs = [{"from": r[0], "to": r[1], "x1": r[2], "y1": r[3], "x2": r[4], "y2": r[5], "active": r[6]} for r in cur.fetchall()]
          
        with graph_manager.lock:
            if floor not in graph_manager.graphs:
                graph_manager.graphs[floor] = nx.Graph()
            if nodes or arcs:
                graph_manager.load_graph(floor, nodes, arcs)

        G = graph_manager.graphs[floor]    
        if not G:
            return JSONResponse({"nodes": [], "arcs": []}, headers=headers)    
        
        nodes = [{"id": n, **d} for n, d in G.nodes(data=True)]
        edges = [{"from": u, "to": v, **d} for u, v, d in G.edges(data=True)]

        print(f"Returning {len(nodes)} nodes and {len(edges)} edges for floor {floor}")
        return JSONResponse({"nodes": nodes, "arcs": edges}, headers=headers)
    finally:
        cur.close()
        conn.close()

@app.get("/api/node-types")
def get_node_types():
    types_list = [
        {"type": key, "display_name": info["display_name"], **({"capacity": info["capacity"]} if "capacity" in info else {})}
        for key, info in NODE_TYPES.items()
    ]
    return JSONResponse(content={"node_types": types_list})

@app.post("/api/reload-graph")
def reload_graph():
    with graph_manager.lock:
        graph_manager.graphs.clear()  
    preload_graphs()  
    return {"message": "Graph reloaded from database"}

@app.get("/")
async def get_index():
    index_path = os.path.join(PUBLIC_FOLDER, "index.html")
    return FileResponse(index_path)