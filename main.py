import subprocess
import threading
import signal
import os
import time
import webbrowser

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
shutdown_event = threading.Event()
processes = {}

SERVICES = {
    "MapViewer":        ["uvicorn", "MapViewer.main:app", "--reload"],
    "UserSimulator":    ["uvicorn", "UserSimulator.main:app", "--reload", "--port", "8001"],
    "AlertManager":     ["python", "AlertManager/main.py"],
    "PositionManager":  ["python", "PositionManager/main.py"],
    "NotificationCenter":["python", "-m", "NotificationCenter.main"],
    "MapManager":       ["python", "-m", "MapManager.main"]
}

monitor_targets = [
    {
        "name": "NotificationCenter",
        "log_file":  os.path.join(BASE_DIR, "NotificationCenter", "logs", "alertConsumer.log"),
        "trigger_text": '"msgType": "Stop"'
    },
    {
        "name": "PositionManager",
        "log_file":  os.path.join(BASE_DIR, "PositionManager", "logs", "positionManager.log"),
        "trigger_text": "FINISHED_POSITIONS"
    }
]

def run_process(name, cmd):
    print(f"[START] {name}")
    p = subprocess.Popen(cmd, cwd=BASE_DIR,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    processes[name] = p

def wait_for_configuration_flag():
    """ Blocks until MapViewer writes the config_completed.flag file """
    flag = os.path.join(BASE_DIR, "config_completed.flag")
    
    while not shutdown_event.is_set() and not os.path.exists(flag):
        time.sleep(0.5)
    if shutdown_event.is_set():
        return

    for svc in ("UserSimulator", "AlertManager", "PositionManager", "NotificationCenter", "MapManager"):
        run_process(svc, SERVICES[svc])

def monitor_logs():
    last_pos = {t["name"]: 0 for t in monitor_targets}
    while not shutdown_event.is_set():
        for tgt in monitor_targets:
            try:
                with open(tgt["log_file"], "r") as f:
                    f.seek(last_pos[tgt["name"]])
                    lines = f.readlines()
                    last_pos[tgt["name"]] = f.tell()
                for L in lines:
                    if tgt["trigger_text"] in L:
                        print(f"[TRIGGER] {tgt['trigger_text']} in {tgt['name']}")
                        shutdown_event.set()
                        return
            except FileNotFoundError:
                pass
        time.sleep(1)
        
def shutdown_all():
    print("[SHUTDOWN] Terminating all services…")
    for name, p in processes.items():
        if p.poll() is None:
            try:
                p.send_signal(signal.SIGINT)
                p.terminate()
                print(f"[STOPPED] {name}")
            except:
                pass

def main():
    # 1) MapViewer
    run_process("MapViewer", SERVICES["MapViewer"])
    time.sleep(1)
    try:
        webbrowser.open("http://127.0.0.1:8000")
    except:
        pass

    # 2) Start thread to wait for configuration flag
    threading.Thread(target=wait_for_configuration_flag, daemon=True).start()
    # 3) Start log monitoring thread
    threading.Thread(target=monitor_logs, daemon=True).start()

    # 4) Main loop: waits for shutdown_event
    try:
        while not shutdown_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[CTRL+C] Interrupted by user.")
        shutdown_event.set()
    finally:
        shutdown_all()

if __name__ == "__main__":
    main()
