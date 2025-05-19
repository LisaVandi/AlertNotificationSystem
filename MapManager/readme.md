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