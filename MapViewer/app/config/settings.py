DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "map_position_db",
    "user": "postgres",
    "password": "postgres"
}

SCALE_CONFIG = {
    "scale_factor": 200,
    "pixels_per_cm": 37.8, 
    "edge_threshold_cm": 15,  
    "min_area_px": 1000, 
    "default_node_capacity_per_sqm": 0.5,  # Default node capacity per square meter
}

NODE_TYPES = {
    "classroom": {
        "display_name": "Classroom",
        "capacity": 50
    },
    "office": {
        "display_name": "Office",
        "capacity": 3
    },
    "coffee_shop": {
        "display_name": "Coffee Shop",
        "capacity": 100
    },
    "canteen": {
        "display_name": "Canteen",
        "capacity": 100
    },
    "bathroom": {
        "display_name": "Bathroom",
        "capacity": 10
    },
    "stairs": {
        "display_name": "Stairs",
        "capacity": 100
    },
    "corridor": {
        "display_name": "Corridor",
        "capacity": 100
    }, 
    "outdoor": {
        "display_name": "Outdoor",
        "capacity": 1000
    }
}

Z_RANGES = {
    "base_z": 0,
    "height_per_floor": 3,
    "z_start_at_floor_zero": True
}