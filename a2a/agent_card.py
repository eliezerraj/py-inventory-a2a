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
            "id": "INVENTORY_CLUSTER_FIT",
            "name": "Inventory Cluster Fit",
            "description": "Performs clustering analysis on inventory data to identify patterns and optimize stock levels.",
            "tags": ["inventory", "analytics", "clustering"],
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product": {
                        "type": "object",
                        "properties": {
                        "sku": { "type": "string" }
                        },
                        "required": "sku"
                    }
                }
            },
            "examples": '{"product": {"sku": "coffee-12"}}',
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
        },
        {
            "id": "INVENTORY_CLUSTER_DATA",
            "name": "Inventory Cluster Data",
            "description": "Provides detailed data from clustering analysis on inventory to support decision-making.",
            "tags": ["inventory", "analytics", "clustering"],
            "inputSchema": {
                "type": "object",
                "properties": {
                "product": {
                    "type": "object",
                    "properties": {
                    "sku": { "type": "string" }
                    },
                    "required": "sku"
                    }
                }
            },
            "examples": '{"product": {"sku": "coffee-12"}}',
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
        },
        {
            "id": "INVENTORY_RUNOUT_ANALYSIS",
            "name": "Inventory Runout Analysis",
            "description": "Calculates days of cover based on inventory availability and pending demand trends.",
            "tags": ["inventory", "forecasting", "runout"],
            "inputSchema": {
                "type": "object",
                "properties": {
                "product": {
                    "type": "object",
                    "properties": {
                    "sku": { "type": "string" }
                    },
                    "required": "sku"
                    }
                }
            },
            "examples": '{"product": {"sku": "coffee-12"}}',
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
        }
    ]
}