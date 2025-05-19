import subprocess
import threading
import signal
import os
import time

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
CHECK_INTERVAL = 2  # secondi tra un controllo e l’altro
shutdown_event = threading.Event()
processes = {}

# Comandi da eseguire nell’ordine specificato
startup_sequence = [
    ("MapViewer uvicorn", ["uvicorn", "MapViewer.main:app", "--reload"]),
    ("NotificationCenter", ["python", "-m", "NotificationCenter.main"]),
    ("MapManager", ["python", "MapManager/main.py"]),
    ("AlertManager", ["python", "AlertManager/main.py"]),
    ("UserSimulator", ["python", "UserSimulator/main.py"]),
    ("PositionManager", ["python", "PositionManager/main.py"]),
]

# File da monitorare e segnali da cercare
monitor_targets = [
    {
        "name": "NotificationCenter",
        "log_file": os.path.join(LOG_DIR, "alertConsumer.log"),
        "trigger_text": '"msgType": "Cancel"'
    },
    {
        "name": "PositionManager",
        "log_file": os.path.join(LOG_DIR, "positionManager.log"),
        "trigger_text": "FINISHED_POSITIONS"
    }
]


def run_process(name, cmd):
    print(f"[START] {name}")
    log_file_path = os.path.join(LOG_DIR, f"{name.replace(' ', '_').lower()}.log")
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    with open(log_file_path, "w") as log_file:
        proc = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=log_file,  # Log del comando
            stderr=subprocess.STDOUT
        )
        processes[name] = proc



def monitor_logs():
    last_positions = {t['name']: 0 for t in monitor_targets}

    while not shutdown_event.is_set():
        for target in monitor_targets:
            try:
                with open(target["log_file"], "r") as f:
                    f.seek(last_positions[target["name"]])
                    new_lines = f.readlines()
                    last_positions[target["name"]] = f.tell()

                for line in new_lines:
                    if target["trigger_text"] in line:
                        print(f"[TRIGGER] Rilevato '{target['trigger_text']}' in {target['log_file']}")
                        shutdown_event.set()
                        return
            except FileNotFoundError:
                pass  # può succedere se il log non è stato ancora creato
        time.sleep(CHECK_INTERVAL)


def shutdown_all():
    print("[SHUTDOWN] Terminazione dei microservizi...")
    for name, proc in processes.items():
        if proc.poll() is None:
            try:
                proc.send_signal(signal.SIGINT)
                proc.terminate()
                print(f"[STOPPED] {name}")
            except Exception as e:
                print(f"[WARN] Errore nel terminare {name}: {e}")


def main():
    # Avvio microservizi
    for name, cmd in startup_sequence:
        run_process(name, cmd)
        time.sleep(1.5)  # Ritardo opzionale

    print("\n[INFO] Tutti i microservizi sono stati avviati. Monitoraggio in corso...\n")

    # Avvio thread per controllare i log
    monitor_thread = threading.Thread(target=monitor_logs, daemon=True)
    monitor_thread.start()

    try:
        while not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[CTRL+C] Interruzione manuale.")
        shutdown_event.set()
    finally:
        shutdown_all()


if __name__ == "__main__":
    main()
