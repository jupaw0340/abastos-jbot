import json
import sys
import requests

phone = "5214435457194"
text = " ".join(sys.argv[1:]).strip()

if not text:
    print("Uso: python scripts/test_whatsapp.py pedido")
    raise SystemExit(1)

payload = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "from": phone,
                                "type": "text",
                                "text": {"body": text},
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

r = requests.post(
    "http://127.0.0.1:8000/webhook",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload),
    timeout=10,
)

print(r.status_code, r.text)
