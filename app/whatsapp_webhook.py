import requests
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from app import config
from app.logging_setup import get_logger
from app.pipeline import PipelineError, answer_question
from app.session import Session

log = get_logger(__name__)
app = FastAPI()

_sessions: dict[str, Session] = {}  # keyed by sender's WhatsApp number
_seen_message_ids: set[str] = set()  # dedup Meta's retried webhook deliveries


def _send_reply(to: str, text: str) -> None:
    url = f"https://graph.facebook.com/v21.0/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if not resp.ok:
        log.error("WhatsApp send failed: %s", resp.text)


@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == config.WHATSAPP_VERIFY_TOKEN
    ):
        return PlainTextResponse(params.get("hub.challenge", ""))
    return PlainTextResponse("Forbidden", status_code=403)


@app.post("/webhook")
async def receive(request: Request):
    body = await request.json()
    try:
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    except (KeyError, IndexError):
        return {"status": "ignored"}  # status update / non-message event

    message_id = message.get("id")
    if message_id in _seen_message_ids:
        log.info("Duplicate webhook delivery for message %s, ignoring", message_id)
        return {"status": "duplicate"}
    _seen_message_ids.add(message_id)

    sender = message["from"]
    question = message.get("text", {}).get("body", "")
    log.info("WhatsApp message from %s: %s", sender, question)

    session = _sessions.setdefault(sender, Session())
    try:
        answer, _, _ = answer_question(question, session)
    except PipelineError as e:
        answer = str(e)

    _send_reply(sender, answer)
    return {"status": "ok"}
