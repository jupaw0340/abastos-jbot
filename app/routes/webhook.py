import requests
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.services.whatsapp_flow import get_text_from_message, handle_incoming_text

router = APIRouter()


def send_whatsapp_text(to: str, text: str):
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        print("SIMULATED WHATSAPP TO", to, ":", text)
        return

    url = f"https://graph.facebook.com/v20.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    requests.post(url, headers=headers, json=payload, timeout=15)


@router.get("/webhook")
def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(challenge or "")

    return PlainTextResponse("Forbidden", status_code=403)


@router.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()

    try:
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"ok": True}

        message = messages[0]
        phone = message.get("from")
        text = get_text_from_message(message)

        if phone and text:
            response = handle_incoming_text(phone, text)
            send_whatsapp_text(phone, response)

    except Exception as e:
        print("WEBHOOK ERROR:", e)

    return {"ok": True}
