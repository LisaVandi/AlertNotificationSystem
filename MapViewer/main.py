import cv2
import psycopg2
import re
import os

from fastapi import Body, FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from MapViewer.app.services.graph_exporter import get_graph_json
from MapViewer.app.services.graph_extractor import extract_nodes_and_edges_from_map, insert_graph_into_db
from MapViewer.app.services.graph_manager import GraphManager
from MapViewer.app.config.settings import DATABASE_CONFIG, NODE_TYPES
from MapViewer.db.db_connection import create_connection
from MapViewer.db.db_setup import create_tables

app = FastAPI()
graph_manager = GraphManager()

IMG_FOLDER = "MapViewer/public/img"
PUBLIC_FOLDER = "MapViewer/public"
JSON_OUTPUT_FOLDER = os.path.join(PUBLIC_FOLDER, "json")

# Mount public directory to serve frontend and images
app.mount("/MapViewer/public", StaticFiles(directory=PUBLIC_FOLDER), name="public")
connected_websockets = set()

conn = create_connection()
create_tables()
conn.close()

def generate_all_graphs_from_images_if_needed():
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nodes")
        node_count = cur.fetchone()[0]
        cur.close()
        conn.close()

        if node_count > 0:
            print(f"[INFO] {node_count} nodes already exist. Skipping graph generation.")
            return

        print("[INFO] Generating graphs from image files...")

        for filename in os.listdir(IMG_FOLDER):
            if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            match = re.search(r'floor(\d+)', filename, re.IGNORECASE)
            if not match:
                continue

            floor_level = int(match.group(1))
            image_path = os.path.join(IMG_FOLDER, filename)
            img = cv2.imread(image_path)
            if img is None:
                print(f"[WARNING] Could not read image {image_path}")
                continue
            height, width = img.shape[:2]

            nodes, arcs = extract_nodes_and_edges_from_map(image_path, floor_level)
            insert_graph_into_db(nodes, arcs, floor_level)

            output_path = os.path.join(JSON_OUTPUT_FOLDER, f"floor{floor_level}.json")
            graph_data = get_graph_json(
                floor_level=floor_level,
                image_filename=filename,
                image_width=width,
                image_height=height,
                output_path=output_path
            )
            graph_manager.load_graph(floor_level, graph_data["nodes"], graph_data["arcs"])
            
        print("[INFO] Graphs and JSON files generated.")
    except Exception as e:
        print(f"[ERROR] Error during automatic graph generation: {e}")

generate_all_graphs_from_images_if_needed()

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

@app.post("/api/generate-json")
def generate_json(
    floor: int = Body(...),
    image_filename: str = Body(...),
    image_width: int = Body(...),
    image_height: int = Body(...)
):
    output_path = os.path.join(JSON_OUTPUT_FOLDER, f"floor{floor}.json")
    data = get_graph_json(floor, image_filename, image_width, image_height, output_path=output_path)
    return JSONResponse(content={"message": f"{output_path} successfully created.", "json_preview": data})

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
    """
    Restituisce i tipi di nodo in formato array, es:
    {
      "node_types": [
        { "type": "classroom", "display_name": "Classroom", "capacity": 5 },
        … 
      ]
    }
    """
    types_list = [
        {"type": key, "display_name": info["display_name"], **({"capacity": info["capacity"]} if "capacity" in info else {})}
        for key, info in NODE_TYPES.items()
    ]
    return JSONResponse(content={"node_types": types_list})
