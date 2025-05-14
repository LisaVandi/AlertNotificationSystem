AlertManager Microservice
Overview

AlertManager handles the lifecycle of CAP messages, including generation, filtering, storage, and forwarding. The system is modular and provides flexibility in how alerts are processed, making it adaptable to various use cases where CAP messages need to be filtered and managed effectively.

Key features of the system include:

    CAP Message Filtering: Based on configurable rules (e.g., event type, region, and severity).

    Message Storage: Processed CAP messages are stored in a database for further analysis.

    Notification Handling: Processed alerts can be sent to a central notification system.

The system is designed to work with real-time CAP data, responding to changes dynamically as new alerts are received.

Configuration

The configuration for AlertManager is primarily defined in the filter_config.yaml file located in the config/ directory. This file contains rules and filters for processing incoming CAP messages, specifying which messages should be processed based on specific criteria such as event type, region, and severity.

Additional Notes

    The system is designed to be modular and can be extended with additional filters or integrated with other alerting systems.

    Custom filters can be easily added to the filter_config.yaml file to match your specific use cases.

