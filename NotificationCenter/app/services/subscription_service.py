# from NotificationCenter.app.services.database_handler import get_db_connection

# def subscribe_user(user_id, subscription_type, subscription_channel):
#     conn = get_db_connection()
#     cursor = conn.cursor()
    
#     cursor.execute("""
#         INSERT INTO user_subscriptions (user_id, subscription_type, subscription_channel)
#         VALUES (%s, %s, %s)
#         ON CONFLICT (user_id) 
#         DO UPDATE SET is_subscribed = TRUE;
#     """, (user_id, subscription_type, subscription_channel))
    
#     conn.commit()
#     conn.close()
