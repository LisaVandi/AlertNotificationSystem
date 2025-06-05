DELETE FROM arc_status_log;
DELETE FROM arcs;
DELETE FROM user_historical_position;
DELETE FROM current_position;
DELETE FROM nodes;
ALTER SEQUENCE nodes_node_id_seq RESTART WITH 1;
ALTER SEQUENCE arcs_arc_id_seq RESTART WITH 1;
SELECT setval('nodes_node_id_seq', (SELECT MAX(node_id) FROM nodes));
SELECT setval('arcs_arc_id_seq', (SELECT MAX(arc_id) FROM arcs));


L’utente apre pagina: carichi grafo tramite REST e lo disegni.

L’utente clicca su "Aggiungi nodo": invii richiesta POST al backend, il backend aggiorna DB e grafo in memoria.

L’utente clicca su "Aggiungi arco": idem POST che aggiorna sia il grafo in memoria che il database.

L’utente clicca su "Aggiorna grafo": il frontend fa GET per ricaricare tutto il grafo da backend e ridisegna.


L’utente clicca sulla mappa → catturi evento click e ricavi coordinate pixel/map.
Mostri all’utente un piccolo pannello o popup per scegliere il tipo di nodo (es. select con tipi nodi).
Quando l’utente conferma (es. clicca su “Aggiungi nodo”), fai POST all’API /api/nodes con:
{
  "x_px": <coordinata_x>,
  "y_px": <coordinata_y>,
  "floor": <floor_corrente>,
  "node_type": "<tipo_scelto>"
}
Al ritorno della risposta (il nuovo nodo con ID), lo disegni subito sulla mappa senza ricaricare.


Apertura pagina:
init() carica immagini e tipi di nodo, crea mappe Leaflet, e chiama loadGraph per ogni piano.

I nodi e gli archi sono disegnati con createNodeMarker e L.polyline.

Aggiunta nodo:
Click sulla mappa → addClickListener cattura coordinate e mostra node-type-selector.

Selezione tipo e click su "Aggiungi nodo" → POST a /api/nodes → graph_manager.add_node → nodo disegnato con createNodeMarker.

Aggiunta arco:
Click su "Aggiungi arco" → isAddingEdge = true.

Click su due nodi → POST a /api/edges → graph_manager.add_edge → arco disegnato con L.polyline.

Aggiornamento grafo:
Click su "Aggiorna grafo" → GET a /api/in-memory-graph → loadGraph ridisegna tutto.

Quando aggiungi un nodo (es. click dal frontend) passi le coordinate pixel, che vengono convertite in cm per il DB.

Quando carichi il grafo dal DB, i dati in cm vengono riconvertiti in pixel per il disegno sulla mappa.

Lo stesso vale per gli archi.

In memoria (networkx), mantieni sempre le coordinate in pixel per semplicità di disegno.