# py-inventory-a2a

py-inventory-a2a

### Endpoint

    curl --location 'http://localhost:7100/a2a/message' \
    --header 'x-request-id: teste-22222222222' \
    --header 'Content-Type: application/json' \
    --data '{
        "source_agent": "user-postman",
        "target_agent": "inventory-agent",
        "message_type": "INVENTORY_RUNOUT_ANALYSIS",
        "payload": {
            "product": {
                "sku": "coffee-100"
            }
        }
    }'

    curl --location 'http://localhost:7100/a2a/message' \
    --header 'Content-Type: application/json' \
    --data '{
        "source_agent": "user-postman",
        "target_agent": "inventory-agent",
        "message_type": "PRICE_ANALYSIS",
        "payload": {
            "product": [ 
                {
                "sku": "coffee-100"
                },
                {
                "sku": "coffee-101"
                },
                {
                "sku": "coffee-102"
                },
                {
                "sku": "coffee-103"
                }
            ]
        }
    }'