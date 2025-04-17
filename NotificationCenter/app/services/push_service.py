from app.services.database_handler import get_db_connection

def send_push_notification(user_id, message):
    # Invia una notifica push all'utente (simulato con un print per il momento)
    print(f"Sending push notification to user {user_id}: {message}")

def send_alert_notification(alert_message):
    # Ottieni tutti gli utenti sottoscritti agli alert
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id, subscription_channel
        FROM user_subscriptions
        WHERE subscription_type = 'alert' AND is_subscribed = TRUE;
    """)
    subscribers = cursor.fetchall()
    
    conn.close()

    # Invia notifiche push agli utenti sottoscritti
    for subscriber in subscribers:
        user_id, subscription_channel = subscriber
        if subscription_channel == 'push':
            send_push_notification(user_id, alert_message)
            
