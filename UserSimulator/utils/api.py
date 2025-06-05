from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from UserSimulator.utils.logger import logger

app = FastAPI()

# Allow CORS for testing, adjust origins as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

simulator_instance = None

@app.get("/positions")
async def get_positions():
    logger.info("Received request for /positions")
    if simulator_instance:
        positions = list(simulator_instance.users_positions.values())
        logger.info(f"Returning positions for {len(positions)} users")
        return JSONResponse(content={"positions": positions})
    else:
        logger.warning("Simulator instance not ready - cannot provide positions")
        return JSONResponse(status_code=503, content={"error": "Simulator not ready"})
