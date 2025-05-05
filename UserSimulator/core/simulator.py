import random
from datetime import datetime

def get_current_slot(config):
    now = datetime.now().time()
    for slot in config["time_slots"]:
        start = datetime.strptime(slot["start"], "%H:%M").time()
        end = datetime.strptime(slot["end"], "%H:%M").time()
        if start <= now < end:
            return slot
    return None

def simulate_user_positions(config, num_users):
    slot = get_current_slot(config)
    if not slot:
        return []
    locations = list(slot["distribution"].keys())
    weights = list(slot["distribution"].values())
    return random.choices(locations, weights=weights, k=num_users)
