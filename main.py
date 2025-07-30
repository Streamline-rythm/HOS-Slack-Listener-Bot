import os
import json
import time
import hmac
import hashlib
import requests
from fastapi import FastAPI, Request, Header, HTTPException, Response
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# Configuration
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")  # Slack channel ID
PORT = int(os.environ.get("PORT", 8080))
# FORWARD_ENDPOINT = os.environ.get("FORWARD_ENDPOINT")  # URL to forward replies to

app = FastAPI()

# Slack request verification
def verify_slack_request(body: bytes, timestamp: str, slack_signature: str) -> bool:
    if not timestamp or not slack_signature:
        return False
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, slack_signature)

@app.post("/slack/events")
async def slack_events(
    request: Request,
    x_slack_request_timestamp: str = Header(None),
    x_slack_signature: str = Header(None),
):
    body = await request.body()

    if not verify_slack_request(body, x_slack_request_timestamp, x_slack_signature):
        raise HTTPException(status_code=403, detail="Invalid request signature")

    data = json.loads(body)

    if data.get("type") != "event_callback":
        return Response(status_code=200)

    event = data.get("event", {})

    # Only capture replies (not original thread messages) in specific channel
    if (
        event.get("type") == "message"
        and not event.get("subtype")
        and event.get("channel") == TARGET_CHANNEL
        and "thread_ts" in event
        and event["ts"] != event["thread_ts"]
    ):  
        print(f"event = {event}")

        payload = {
            "user": event.get("user"),
            "text": event.get("text"),
            "thread_ts": event.get("thread_ts"),
            "ts": event.get("ts"),
            "channel": event.get("channel"),
        }

        print(f"payload= {payload}")
        # try:
        #     response = requests.post(FORWARD_ENDPOINT, json=payload)
        #     print(f"Forwarded reply: {response.status_code}")
        # except Exception as e:
        #     print(f"Error forwarding reply: {e}")

    return Response(status_code=200)

if __name__ == "__main__":
    print(f"Listening for Slack replies on port {PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
