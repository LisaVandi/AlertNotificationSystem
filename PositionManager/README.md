PositionManager Microservice
Overview

The PositionManager microservice handles the processing of user position data and related evacuation events. It listens to messages from a RabbitMQ queue, processes these messages, and updates the database with the user's position and associated danger information. It also sends aggregated data to other microservices based on configured rules. The service connects to a PostgreSQL database (map_position_db) and communicates with other microservices using RabbitMQ.

Responsibilities

    Position Management: Process and store the current positions of users in the database.

    Danger Information: Determine if the user is in danger based on the event type and store this information in the database.

    Evacuation Paths: Send evacuation path data to other microservices for users in danger.

    Event Handling: Process different event types such as Flood, Earthquake, Fire, etc., and apply evacuation logic based on these events.

Conclusion

The PositionManager microservice plays a critical role in managing the positions of users, determining the danger level based on event types, and ensuring that relevant information is passed on to other services. Through proper configuration, it can handle various event types and provide accurate evacuation paths to users in danger.