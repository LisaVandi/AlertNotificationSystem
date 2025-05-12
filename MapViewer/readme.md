DELETE FROM arc_status_log;
DELETE FROM arcs;
DELETE FROM nodes;
ALTER SEQUENCE nodes_node_id_seq RESTART WITH 1;
ALTER SEQUENCE arcs_arc_id_seq RESTART WITH 1;


- voglio definire il punto (0,0) nell''immagine della piantina per gestire le coordinate a partire da quel punto con la scala definita nel file di configurazione
- voglio creare un'interfaccia utente con la visualizzazione del grafo associato alle immagini presenti nella cartella img. Cliccando su ogni nodo del grafo, l'utente può selezionare la tipologia di nodo (esplicitato nel file di configurazione dedicato), e tale click poi andrà ad aggiornare la tipologia di nodo sul db
- voglio definire una funzione che associa al numero di piano l'altezza corrispondente ( procedura che prende in input altezza e posizione e poi funzione di mapping che processa)
-  voglio ampliare la grandezza del nodo in base al numero di persone presenti su di esso (campo della tabella nodes).
- salvare il grafo con python (non query ogni volta)