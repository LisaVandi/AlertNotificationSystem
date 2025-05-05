-- Function to log changes in arc's 'active' state
CREATE OR REPLACE FUNCTION log_arc_status_change() 
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.active <> OLD.active THEN
        INSERT INTO arc_status_log (arc_id, previous_state, new_state, modified_by)
        VALUES (NEW.arc_id, OLD.active, NEW.active, 'system');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger that will call the log function after each update on the arcs table
CREATE TRIGGER trigger_arc_status_change
AFTER UPDATE OF active ON arcs
FOR EACH ROW
EXECUTE FUNCTION log_arc_status_change();

-- -- 
-- CREATE OR REPLACE FUNCTION notify_map_update()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     -- Notification for map update 
--     PERFORM pg_notify('map_update', 'Updated position for user ' || NEW.user_id);
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- -- Trigger che emette la notifica ogni volta che una posizione viene aggiornata
-- CREATE TRIGGER trigger_map_update
-- AFTER UPDATE ON current_position
-- FOR EACH ROW
-- EXECUTE FUNCTION notify_map_update();
