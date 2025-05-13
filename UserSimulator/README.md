Cosa fa l'UserSimulator
1. Ascolta due code:
user_simulator_queue:

Se riceve msgType = "Stop" → si ferma.

Se riceve msgType = "Alert" →

Legge numero e tipo di utenti da simulare da un file YAML.

Recupera i nodi dal DB (nodes da map_position_db).

Genera per ciascun utente una posizione casuale interna al nodo selezionato.

Aggiunge event preso dal messaggio originale.

Invia a position_queue un messaggio con:
user_id, x, y, z, id_nodo, event.

evacuation_paths_queue:

Riceve: { "user_id": ..., "evacuation_path": ["arc_id1", "arc_id2", ...] }

Recupera la posizione attuale dell'utente da current_position in map_position_db.

Per ogni arc_id del path:

Cerca nella tabella archs l'arco corrispondente.

Prende il final_node.

Simula nuova posizione (x, y, z) interna al final_node.

Invia nuovo messaggio a position_queue:
user_id, x, y, z, id_nodo (senza event questa volta).