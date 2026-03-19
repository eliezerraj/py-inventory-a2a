from infrastructure.config.config import settings

AGENT_CARD = {
    "name": settings.APP_NAME,
    "description": "Inventory agent handles inventory management and optimization tasks, providing real-time insights and recommendations to ensure efficient stock levels and reduce costs.",
    "version": settings.VERSION,
    "provider": {
        "organization": "eliezer-junior Org.",
        "url": settings.URL_AGENT,
    },
    "documentationUrl": f"{settings.URL_AGENT}/info",
    "supportedInterfaces": [
        {
            "url": f"{settings.URL_AGENT}/a2a/message",
            "protocolBinding": "HTTP+JSON",
            "protocolVersion": "1.0",
        }        
    ],
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": False,
        "extendedAgentCard": False,
    },
    "defaultInputModes": ["application/json"],
    "defaultOutputModes": ["application/json"],
    "skills": [
        {
            "id": "PRICE_ANALYSIS",
            "name": "Price Analysis",
            "description": "Analyzes product pricing and quantity trends from cart item history.",
            "tags": ["inventory", "pricing", "analytics"],
            "examples": [
                '{"product": [{"sku": "coffee-12"}]}'
            ],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
        },
        {
            "id": "INVENTORY_RUNOUT_ANALYSIS",
            "name": "Inventory Runout Analysis",
            "description": "Calculates days of cover based on inventory availability and pending demand trends.",
            "tags": ["inventory", "forecasting", "runout"],
            "examples": [
                '{"product": {"sku": "coffee-12"}}'
            ],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
        }
    ]
}