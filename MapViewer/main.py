import asyncio
import threading
import cv2
import psycopg2
import re
import os

from fastapi import Body, FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from MapViewer.app.services.graph_exporter import get_graph_json
from MapViewer.app.services.graph_extractor import extract_nodes_and_edges_from_map, insert_graph_into_db
from MapViewer.app.config.settings import DATABASE_CONFIG
from MapViewer.db.db_connection import create_connection
from MapViewer.db.db_setup import create_tables

app = FastAPI()

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
            get_graph_json(
                floor_level=floor_level,
                image_filename=filename,
                image_width=width,
                image_height=height,
                output_path=output_path
            )

        print("[INFO] Graphs and JSON files generated.")
    except Exception as e:
        print(f"[ERROR] Error during automatic graph generation: {e}")

generate_all_graphs_from_images_if_needed()

def notify_clients():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        conn.set_isolation_level(0)
        cur = conn.cursor()
        cur.execute("LISTEN update_trigger;")
        while True:
            conn.poll()
            while conn.notifies:
                conn.notifies.pop()
                coro = broadcast_update()
                asyncio.run_coroutine_threadsafe(coro, loop)

async def broadcast_update():
    for ws in connected_websockets:
        try:
            await ws.send_text("update")
        except:
            pass

threading.Thread(target=notify_clients, daemon=True).start()

@app.get("/api/images")
def list_images():
    files = [f for f in os.listdir(IMG_FOLDER) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    return JSONResponse(content={"images": files})

@app.get("/api/map")
def get_map(
    floor: int = Query(...),
    image_filename: str = Query(...),
    image_width: int = Query(...),
    image_height: int = Query(...)
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
