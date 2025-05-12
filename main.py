import subprocess
import threading
import signal
import os
import time

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Definizione dei comandi da eseguire (nome leggibile + comando)
commands = [
    ("MapViewer websocket", ["python", "-m", "MapViewer.app.websocket_server"]),
    ("MapViewer uvicorn", ["uvicorn", "MapViewer.main:app", "--reload"]),
    ("NotificationCenter", ["python", "-m", "NotificationCenter.main"]),
    ("AlertManager", ["python", "AlertManager/main.py"]),
    ("UserSimulator", ["python", "UserSimulator/main.py"]),
    ("PositionManager", ["python", "PositionManager/main.py"]),
    ("MapManager", ["python", "MapManager/main.py"]),
]

processes = []

# Funzione che avvia il processo e stampa il log
def run_process(name, cmd):
    print(f"[START] {name}: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    processes.append(proc)

    try:
        for line in proc.stdout:
            print(f"[{name}] {line.strip()}")
    except Exception as e:
        print(f"[ERROR] {name} crashed with: {e}")

# Avvio dei thread
threads = []

try:
    for name, cmd in commands:
        t = threading.Thread(target=run_process, args=(name, cmd), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(1.5)  # Delay opzionale tra gli avvii

    print("\n[INFO] Tutti i microservizi sono in esecuzione. Premere CTRL+C per terminare.\n")

    # Rende il main thread vivo finché gli altri thread vivono
    for t in threads:
        t.join()

except KeyboardInterrupt:
    print("\n[STOP] Interruzione ricevuta. Terminazione dei microservizi...")
    for proc in processes:
        try:
            proc.send_signal(signal.SIGINT)
            proc.terminate()
        except Exception as e:
            print(f"[WARN] Errore nel terminare un processo: {e}")