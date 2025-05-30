# import subprocess
# import threading
# import signal
# import os
# import time
# import webbrowser

# BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# shutdown_event = threading.Event()
# processes = {}

# startup_sequence = [
#     ("MapViewer uvicorn", ["uvicorn", "MapViewer.main:app", "--reload"]),
#     ("NotificationCenter", ["python", "-m", "NotificationCenter.main"]),
#     ("AlertManager", ["python", "AlertManager/main.py"]),
#     ("UserSimulator", ["python", "UserSimulator/main.py"]),
#     ("PositionManager", ["python", "PositionManager/main.py"]),
#     ("MapManager", ["python", "-m", "MapManager.main"]),
# ]

# monitor_targets = [
#     {
#         "name": "NotificationCenter",
#         "log_file":  os.path.join(BASE_DIR, "NotificationCenter", "logs", "alertConsumer.log"), 
#         "trigger_text": '"msgType": "Cancel"'
#     },
#     {
#         "name": "PositionManager",
#         "log_file":  os.path.join(BASE_DIR, "PositionManager", "logs", "positionManager.log"),
#         "trigger_text": "FINISHED_POSITIONS"
#     }
# ]


# def run_process(name, cmd):
#     print(f"[START] {name}")
#     proc = subprocess.Popen(
#         cmd,
#         cwd=BASE_DIR,
#         stdout=subprocess.DEVNULL,
#         stderr=subprocess.DEVNULL
#     )
#     processes[name] = proc
        

# def monitor_logs():
#     last_positions = {t['name']: 0 for t in monitor_targets}

#     while not shutdown_event.is_set():
#         for target in monitor_targets:
#             try:
#                 with open(target["log_file"], "r") as f:
#                     f.seek(last_positions[target["name"]])
#                     new_lines = f.readlines()
#                     last_positions[target["name"]] = f.tell()

#                 for line in new_lines:
#                     if target["trigger_text"] in line:
#                         print(f"[TRIGGER] '{target['trigger_text']}' detected in {target['log_file']}")
#                         shutdown_event.set()
#                         return
#             except FileNotFoundError:
#                 pass  
#         time.sleep(2)


# def shutdown_all():
#     print("[SHUTDOWN] Termination of microservices...")
#     for name, proc in processes.items():
#         if proc.poll() is None:
#             try:
#                 proc.send_signal(signal.SIGINT)
#                 proc.terminate()
#                 print(f"[STOPPED] {name}")
#             except Exception as e:
#                 print(f"[WARN] Error while terminating {name}: {e}")


# def main():
#     config_mode = False
#     if config_mode:
#         startup_sequence_to_run = [startup_sequence[0]]  # solo MapViewer uvicorn
#     else:
#         startup_sequence_to_run = startup_sequence
    
#     for name, cmd in startup_sequence_to_run:
#         run_process(name, cmd)
#         time.sleep(1.5)

#     try:
#         webbrowser.open("http://127.0.0.1:8000")
#         print("[INFO] Open browser on http://127.0.0.1:8000")
#     except Exception as e:
#         print(f"[WARN] Unable to open browser: {e}")
    
#     print("\n[INFO] All microservices have been started. Monitoring in progress...\n")

#     monitor_thread = threading.Thread(target=monitor_logs, daemon=True)
#     monitor_thread.start()

#     try:
#         while not shutdown_event.is_set():
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("\n[CTRL+C] Manual interruption.")
#         shutdown_event.set()
#     finally:
#         shutdown_all()


# if __name__ == "__main__":
#     main()

import os
import time
import subprocess
import threading
import signal

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
shutdown_event = threading.Event()
processes = {}

ALERT_MANAGER_DELAY = 3

startup_sequence = [
    ("MapViewer uvicorn", ["uvicorn", "MapViewer.main:app", "--reload"]),
    ("NotificationCenter", ["python", "-m", "NotificationCenter.main"]),
    ("UserSimulator", ["uvicorn", "UserSimulator.main:app", "--reload"]),
    ("MapManager", ["python", "-m", "MapManager.main"]),
]

def run_process(name, cmd):
    print(f"[START] {name}")
    proc = subprocess.Popen(cmd, cwd=BASE_DIR)
    processes[name] = proc

def start_alert_manager():
    """Funzione separata per avviare AlertManager con delay"""
    time.sleep(ALERT_MANAGER_DELAY)
    run_process("AlertManager", ["python", "AlertManager/main.py"])
    print(f"[INFO] AlertManager started after {ALERT_MANAGER_DELAY} seconds delay")   
    run_process("PositionManager", ["python", "PositionManager/main.py"])
    print(f"[INFO] PositionManager started after {ALERT_MANAGER_DELAY} seconds delay")        
     
         


def shutdown_process(name):
    proc = processes.get(name)
    if proc and proc.poll() is None:
        try:
            proc.send_signal(signal.SIGINT)
            proc.terminate()
            print(f"[STOPPED] {name}")
        except Exception as e:
            print(f"[WARN] Error terminating {name}: {e}")

def monitor_config_flag_and_start_services():
    flag_path = os.path.join(BASE_DIR, "config_completed.flag")
    print("[INFO] Waiting for configuration to complete...")

    while not shutdown_event.is_set():
        if os.path.exists(flag_path):
            print("[INFO] Configuration completed flag detected!")

            # Stop MapViewer
            shutdown_process("MapViewer uvicorn")

            # Start all the other services
            for name, cmd in startup_sequence[1:]:
                run_process(name, cmd)
                time.sleep(1.5)

            print("[INFO] All microservices started after configuration.")

            return  # Stop monitoring

        time.sleep(2)

def main():
    # Start only MapViewer
    run_process(*startup_sequence[0])

    # Open browser
    try:
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000")
    except Exception as e:
        print(f"[WARN] Unable to open browser: {e}")

    # Start thread to monitor configuration completion flag
    monitor_thread = threading.Thread(target=monitor_config_flag_and_start_services, daemon=True)
    monitor_thread.start()

    try:
        while not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[CTRL+C] Manual interruption.")
        shutdown_event.set()
    finally:
        print("[SHUTDOWN] Terminating all services...")
        for name in list(processes.keys()):
            shutdown_process(name)

if __name__ == "__main__":
    main()
