-- CREATE DATABASE subscription_db;

CREATE TABLE user_subscriptions (
    user_id INTEGER PRIMARY KEY,
    subscription_type VARCHAR(50),   
    subscription_channel VARCHAR(50), -- es. "push", "email", ecc.
    is_subscribed BOOLEAN DEFAULT TRUE
);
