DELETE FROM arc_status_log;
DELETE FROM arcs;
DELETE FROM user_historical_position;
DELETE FROM current_position;
DELETE FROM nodes;
ALTER SEQUENCE nodes_node_id_seq RESTART WITH 1;
ALTER SEQUENCE arcs_arc_id_seq RESTART WITH 1;


L’utente apre pagina: carichi grafo tramite REST e lo disegni.

L’utente clicca su "Aggiungi nodo": invii richiesta POST al backend, il backend aggiorna DB e grafo in memoria.

L’utente clicca su "Aggiungi arco": idem POST che aggiorna sia il grafo in memoria che il database.

L’utente clicca su "Aggiorna grafo": il frontend fa GET per ricaricare tutto il grafo da backend e ridisegna.
