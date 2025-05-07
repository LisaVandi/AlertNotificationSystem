import asyncio
import asyncpg
import websockets
from MapViewer.app.config.settings import DATABASE_CONFIG

connected_clients = set()

async def websocket_handler(websocket, path):
    connected_clients.add(websocket)
    try:
        async for _ in websocket:
            pass  # No incoming messages are handled
    finally:
        connected_clients.remove(websocket)

async def listen_pg():
    conn = await asyncpg.connect(
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
        database=DATABASE_CONFIG["database"],
        host=DATABASE_CONFIG["host"],
        port=DATABASE_CONFIG["port"]
    )
    await conn.add_listener('position_update', lambda *args: asyncio.create_task(send_refresh_signal()))

    while True:
        await asyncio.sleep(3600)  # Keeps the listener running

async def send_refresh_signal():
    print("[NOTIFY] PostgreSQL sent 'position_update' → Refreshing clients")
    for client in connected_clients:
        try:
            await client.send("refresh")
        except:
            pass  # Silently ignore broken connections

async def main():
    print("[WS] WebSocket server listening on ws://localhost:8765")
    await asyncio.gather(
        websockets.serve(websocket_handler, "localhost", 8765),
        listen_pg()
    )

if __name__ == "__main__":
    asyncio.run(main())
