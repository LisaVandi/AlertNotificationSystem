# UserSimulator/utils/api.py

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from UserSimulator.utils.logger import logger

def register_api_routes(app: FastAPI, simulator_instance_ref: list):
    # CORS middleware (opzionale per testing locale)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/positions")
    async def get_positions():
        logger.info("Received request for /positions")
        simulator = simulator_instance_ref[0]
        if simulator:
            positions = list(simulator.users_positions.values())
            logger.info(f"Returning positions for {len(positions)} users")
            return JSONResponse(content={"positions": positions})
        else:
            logger.warning("Simulator instance not ready - cannot provide positions")
            return JSONResponse(status_code=503, content={"error": "Simulator not ready"})
