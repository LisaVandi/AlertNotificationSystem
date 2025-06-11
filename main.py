import subprocess
import threading
import signal
import os
import time
import webbrowser

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
shutdown_event = threading.Event()
processes = {}

ALERT_MANAGER_DELAY = 5

startup_sequence = [
    ("MapViewer uvicorn", ["uvicorn", "MapViewer.main:app", "--reload"]),
    ("NotificationCenter", ["python", "-m", "NotificationCenter.main"]),
    ("UserSimulator", ["uvicorn", "UserSimulator.main:app", "--reload", "--port", "8001"]),
    ("MapManager", ["python", "-m", "MapManager.main"]),
]

monitor_targets = [
    {
        "name": "NotificationCenter",
        "log_file":  os.path.join(BASE_DIR, "NotificationCenter", "logs", "alertConsumer.log"), 
        "trigger_text": '"msgType": "Cancel"'
    },
    {
        "name": "PositionManager",
        "log_file":  os.path.join(BASE_DIR, "PositionManager", "logs", "positionManager.log"),
        "trigger_text": "FINISHED_POSITIONS"
    }
]


def run_process(name, cmd):
    print(f"[START] {name}")
    proc = subprocess.Popen(
        cmd,
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    processes[name] = proc

def start_alert_manager():
    """Funzione separata per avviare AlertManager con delay"""
    time.sleep(ALERT_MANAGER_DELAY)
    run_process("AlertManager", ["python", "AlertManager/main.py"])
    print(f"[INFO] AlertManager started after {ALERT_MANAGER_DELAY} seconds delay")   
    run_process("PositionManager", ["python", "PositionManager/main.py"])
    print(f"[INFO] PositionManager started after {ALERT_MANAGER_DELAY} seconds delay")        
     

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
                        print(f"[TRIGGER] '{target['trigger_text']}' detected in {target['log_file']}")
                        shutdown_event.set()
                        return
            except FileNotFoundError:
                pass  
        time.sleep(2)


def shutdown_all():
    print("[SHUTDOWN] Termination of microservices...")
    for name, proc in processes.items():
        if proc.poll() is None:
            try:
                proc.send_signal(signal.SIGINT)
                proc.terminate()
                print(f"[STOPPED] {name}")
            except Exception as e:
                print(f"[WARN] Error while terminating {name}: {e}")


def main():
    for name, cmd in startup_sequence:
        run_process(name, cmd)
        time.sleep(1.5)

    alert_manager_thread = threading.Thread(
        target=start_alert_manager,
        daemon=True
    )
    alert_manager_thread.start()

    try:
        webbrowser.open("http://127.0.0.1:8000")
        print("[INFO] Open browser on http://127.0.0.1:8000")
    except Exception as e:
        print(f"[WARN] Unable to open browser: {e}")
    
    print("\n[INFO] All microservices have been started. Monitoring in progress...\n")

    monitor_thread = threading.Thread(target=monitor_logs, daemon=True)
    monitor_thread.start()

    try:
        while not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[CTRL+C] Manual interruption.")
        shutdown_event.set()
    finally:
        shutdown_all()


if __name__ == "__main__":
    main()