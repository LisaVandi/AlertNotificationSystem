# AlertNotificationSystem

/project-root
│
├── /center-notifications        # Microservizio Centro Notifiche
│   ├── /app
│   │   ├── _init_.py
│   │   ├── controllers/
│   │   │   └── notifications_controller.py
│   │   ├── services/
│   │   │   └── notifications_service.py
│   │   └── models/
│   │       └── notification.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── config/
│       └── config.yaml
│
├── /alert-service               # Microservizio Gestore degli Alert
│   ├── /app
│   │   ├── _init_.py
│   │   ├── controllers/
│   │   │   └── alert_controller.py
│   │   ├── services/
│   │   │   └── alert_service.py
│   │   └── models/
│   │       └── alert.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── config/
│       └── config.yaml
│
├── /position-simulator         # Microservizio Simulatore delle Posizioni
│   ├── /app
│   │   ├── _init_.py
│   │   ├── controllers/
│   │   │   └── simulator_controller.py
│   │   ├── services/
│   │   │   └── simulator_service.py
│   │   └── models/
│   │       └── position.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── config/
│       └── config.yaml
│
├── /position-manager           # Microservizio Gestore delle Posizioni
│   ├── /app
│   │   ├── _init_.py
│   │   ├── controllers/
│   │   │   └── position_controller.py
│   │   ├── services/
│   │   │   └── position_service.py
│   │   └── models/
│   │       └── position_data.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── config/
│       └── config.yaml
│
├── /map-viewer                # Microservizio Visualizzatore della Mappa
│   ├── /app
│   │   ├── _init_.py
│   │   ├── controllers/
│   │   │   └── map_controller.py
│   │   ├── services/
│   │   │   └── map_service.py
│   │   └── models/
│   │       └── map_data.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── config/
│       └── config.yaml
│
├── /map-manager               # Microservizio Gestore della Mappa
│   ├── /app
│   │   ├── _init_.py
│   │   ├── controllers/
│   │   │   └── map_management_controller.py
│   │   ├── services/
│   │   │   └── map_management_service.py
│   │   └── models/
│   │       └── route.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── config/
│       └── config.yaml
│
├── docker-compose.yml         # Docker Compose per orchestrare i microservizi
├── .gitignore                 # Ignora i file non necessari per Git
├── README.md                  # Documentazione del progetto
