from fastapi import APIRouter, HTTPException
from app.services.alert_service import process_cap
from app.utils.cap_utils import get_random_cap

# Create an API router for handling alert-related endpoints
router = APIRouter()

@router.post("/simulate_alert/")
def simulate_alert():
    """
    Simulates an alert by fetching a random CAP XML and processing it.

    Returns:
        dict: Result of the alert processing.
    """
    try:
        # Fetch a random CAP file from the test directory
        cap_content = get_random_cap("test_caps/")

        # Pass the CAP content to the alert processing service
        result = process_cap(cap_content)

        #Return the result of the alert processing (success or rejection)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
