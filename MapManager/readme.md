Riceve dal gestore delle posizioni la lista degli identificativi univoci (id) delle persone interessate all’allerta in formato aggregato in base ai nodi. 
Inizia la propria attività di calcolo di percorsi individuando i percorsi di default per ogni nodo e li salva sul db sul campo  "evacuation_path" di ogni nodo. 
Infatti, accede alla tabella delle posizioni attuali del database delle posizioni e, sulla base delle posizioni degli utenti in allerta, calcola il percorso di evacuazione e lo aggiorna sul database. 
Inoltre, aggiorna lo stato di un arco (attivo/non attivo) sulla base della capacità e di eventuali interruzioni segnalate dagli utenti. 

1. Ricezione dei messaggi via RabbitMQ
Il consumer EvacuationConsumer riceve i messaggi sulla coda RabbitMQ ALERTED_USERS_QUEUE contenenti gli alerted users' IDs and evacuation paths from the Position Manager. Quando un messaggio viene ricevuto, la logica di gestione dei percorsi (handle_evacuations) viene chiamata.
2. Calcolo dei percorsi di evacuazione
Nel modulo manager.py, la funzione handle_evacuations calcola i percorsi per ogni nodo in allerta, ma dobbiamo anche assicurarci che questa logica venga eseguita solo dopo che il grafo è caricato correttamente. Se il grafo non è presente o ha problemi, dobbiamo gestire l'errore e garantire che venga riprovato.
3. Scrittura dei percorsi di evacuazione nel database
Nel modulo db_writer.py, la funzione update_node_evacuation_path aggiorna correttamente i percorsi nel campo evacuation_path della tabella nodes. Assicurati che il percorso venga salvato nel formato corretto (come JSON) e che venga gestito correttamente quando non c'è un percorso disponibile.
4. Aggiornamento degli archi
Nel modulo arc_updater.py, la funzione update_arc_statuses disattiva gli archi sovraccarichi o rotti. Dobbiamo essere sicuri che gli archi vengano disattivati correttamente in base ai flussi e alla capacità.
5. Gestione dei percorsi via path_calculator.py
La funzione find_shortest_path_to_exit implementa algoritmi di path_finding, ma dobbiamo assicurarci che le capacità degli archi (e quindi la loro attivazione/disattivazione) vengano considerate correttamente quando si calcola il percorso più breve.

PERCORSO COME LISTA ORDINATA DI ARCHI (e non di nodi, dal momento che le porte sono considerate nodi)


# MapManager Microservice

## Overview

MapManager is a microservice responsible for managing building floor graphs and calculating evacuation paths for nodes based on emergency events. It maintains an in-memory representation of floor graphs, listens for alerts on dangerous nodes via RabbitMQ, and updates evacuation paths accordingly.

## Features

- Loads floor graphs (nodes and arcs) from the database at startup.
- Calculates shortest evacuation paths from nodes to safe exits based on different emergency event types.
- Supports differentiated evacuation logic for various emergencies (e.g., Fire, Flood, Earthquake).
- Listens on RabbitMQ queue `MAP_MANAGER_QUEUE` for alert messages with dangerous nodes and event type.
- Updates evacuation paths in the database (`nodes.evacuation_path`) with ordered lists of arc IDs representing safe routes.
- Updates arc statuses in case of broken or overloaded arcs.

## Emergency Event Types

MapManager distinguishes emergency types via the `"event"` field received from PositionManager, which impacts pathfinding logic:

| Event      | Logic Description                                                       |
|------------|-------------------------------------------------------------------------|
| Fire       | Users are guided outside the danger zone (a defined rectangular area).  |
| Evacuation | Users are guided to nodes of type `"outdoor"`.                          |
| Flood      | Users must reach nodes of type `"stairs"` to move to upper floors.      |
| Default    | If no `"event"` is provided, defaults to `"Evacuation"` logic.          |

## RabbitMQ Messages

MapManager consumes messages from the `MAP_MANAGER_QUEUE` from the PositionManager microservice. Each message contains:
- An `event` field indicating the emergency type (e.g., `"Fire"`, `"Evacuation"`, `"Flood"`).

- A list of nodes with aggregated user presence, represented as `dangerous_nodes` with node IDs.


## Pathfinding Logic

Based on the event type:

- **Fire**: Paths avoid the danger zone (defined by coordinates from configuration), leading users outside it.

- **Evacuation**: Paths direct users to safe nodes of type `"outdoor"`.

- **Flood**: Paths direct users to nodes of type `"stairs"` to ascend.

- **Others**: Defaults to `"Evacuation"` logic if `event` is missing.

## Evacuation Paths

- Evacuation paths are valid only if they terminate at safe nodes defined per event type.

- For **Fire** events, the danger zone is excluded from the path.

- For **Evacuation** and **Flood** events, paths terminate at the appropriate safe node types.

- If no valid path is found for a node, the evacuation path is stored as an empty list, indicating no route.

---

## Data Storage

- The graph is loaded and kept in memory from the database on service start.

- Evacuation paths are stored in the `evacuation_path` field in the `nodes` table as an ordered list of `arc_id`s representing the route.

- Arc status (`active`/`inactive`) is updated based on capacity and reported damages.


## Summary

The MapManager dynamically calculates personalized evacuation routes tailored to different emergency types, ensuring users are guided safely away from danger zones or towards safe exit points depending on the specific emergency scenario.