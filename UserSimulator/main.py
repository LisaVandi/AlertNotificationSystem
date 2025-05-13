from UserSimulator.simulation.event_listener import listen_for_events
from UserSimulator.utils.logger import logger  # Importa il logger

if __name__ == "__main__":
    try:
        logger.info("Avvio del listener per gli eventi.")
        listen_for_events()  # Avvia l'ascolto degli eventi
        logger.info("Ascolto eventi completato.")  # Questo verrà eseguito quando il listener si ferma
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione del listener: {e}")
