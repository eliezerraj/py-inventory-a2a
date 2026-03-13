from infrastructure.config.config import settings

AGENT_CARD = {
    "name": settings.APP_NAME,
    "version": settings.VERSION,
    "url": settings.URL_AGENT,
    "version": "v1",
    "protocol": "a2a/1.0",
    "description": "Inventory agent handles inventory management and optimization tasks, providing real-time insights and recommendations to ensure efficient stock levels and reduce costs.",
    "maintainer": {
        "contact": "eliezerral@gmail.com",
        "organization": "eliezer-junior Org.",
    },
    "capabilities": [
        {
            "intent": "INVENTORY_MANAGEMENT",
            "consumes": ["INVENTORY_REQUEST"],
            "produces": ["INVENTORY_REQUEST_RESULT"],
            "input_modes": ["application/json"],
            "output_modes": ["application/json"],
            "schema": {
                "type": "object",
                "required": ["sku"],
                "properties": {
                    "sku": { "type": "string" }
                },
            },
        },
    ],
    "skills": {
        "manage_inventory": "Manage inventory levels and optimize stock",
    },
    "endpoints": {
        "message": "/a2a/message",
        "health": "/info",
    },
    "security": {
        "type": "none", 
        "description": "Localhost testing mode"
    }
}