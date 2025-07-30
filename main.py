import os
import json
import time
import hmac
import hashlib
from fastapi import FastAPI, Request, Header, HTTPException, Response
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import uvicorn

# Load environment variables from .env file
load_dotenv()

# FastAPI app
app = FastAPI()

# Load secrets from env
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))

# Slack WebClient
client = WebClient(token=SLACK_BOT_TOKEN)


# Middleware: Verify Slack signature
def verify_slack_request(body: bytes, timestamp: str, slack_signature: str) -> bool:
    if not timestamp or not slack_signature:
        return False

    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False  # Prevent replay attacks

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

    # Handle Slack URL verification
    if data.get("type") == "url_verification":
        return Response(content=data.get("challenge"), media_type="text/plain")

    # Handle Slack event callbacks
    if data.get("type") == "event_callback":
        event = data.get("event", {})

        # Ignore bot messages and edited messages
        if event.get("type") == "message" and not event.get("subtype"):
            user = event.get("user")
            text = event.get("text")
            channel = event.get("channel")

            print(f"Received message from {user} in {channel}: {text}")

            try:
                # Respond to the user
                client.chat_postMessage(
                    channel=channel,
                    text=f'Hi <@{user}>, I received your message: "{text}"'
                )
            except SlackApiError as e:
                print(f"Error posting message: {e.response['error']}")

    return Response(status_code=200)


if __name__ == "__main__":
    print(f"Starting server on port {PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
