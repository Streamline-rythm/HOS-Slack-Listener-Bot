import os
import json
import time
import hmac
import hashlib
import uvicorn
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Header
from dotenv import load_dotenv

from db import pool

load_dotenv()

# Configuration
TARGET_CHANNEL = "C097MNT5HM5"  
PORT = int(os.environ.get("PORT", 8080))
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SLACK_REFLIES_API_URL = "https://slack.com/api/conversations.replies"

app = FastAPI()

# Slack request verification
def verify_slack_request(body: bytes, timestamp: str, slack_signature: str) -> bool:
    # 1. Check if timestamp and signature are present
    if not timestamp or not slack_signature:
        return False

    # 2. Prevent replay attacks (more than 5 minutes old)
    current_time = time.time()
    if abs(current_time - int(timestamp)) > 60 * 5:
        return False

    # 3. Build the signature base string according to Slack’s spec
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"

    # 4. Compute HMAC SHA256 signature using your Slack signing secret
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # 5. Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(my_signature, slack_signature)

def get_parent_message_id(msg):
    try:
        with pool.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT MAX(id) AS max_id FROM messages WHERE content = %s", (msg,))
            result = cursor.fetchone()
            cursor.close()
            print(f"parent_message_id: {result}")
            return result["max_id"] if result and result["max_id"] else None
    except Exception as err:
        print(f"❌ Database error: {err}")
        return None

def get_parent_message(timestamp: str):
    try:
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
        }

        url = f"{SLACK_REFLIES_API_URL}?channel={TARGET_CHANNEL}&ts={timestamp}&limit=1&pretty=1"
        print(f"url= {url}")
        
        response = requests.post(url, headers=headers)  # Use GET for Slack Web API

        if response.status_code != 200:
            print(f"Slack API error: {response.status_code} - {response.text}")
            return None

        data = response.json()

        messages = data.get("messages", [])
        if not messages:
            print("Error getting parent message: No messages found")
            return None

        parent_message = messages[0].get("text", "")
        print(f"Parent message of {timestamp}: {parent_message}")
        convert_parent_message = parent_message.split("[")[-1].replace("`", "").replace("]", "").strip()

        return convert_parent_message

    except Exception as e:
        print(f"Error getting parent messages from Slack: {e}")
        return None

def save_slack_response(message_id, reply_content):
    try:
        with pool.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            reply_at = datetime.utcnow().isoformat()[:19].replace('T', ' ')

            cursor.execute(
                'INSERT INTO replies (message_id, reply_content, reply_at) VALUES (%s, %s, %s)',
                (message_id, reply_content, reply_at)
            )
            conn.commit()  # Important: commit the insert
            cursor.close()
            conn.close()
            result = {
                "message_id": message_id,
                "reply_content": reply_content,
                "reply_at": reply_at
            }
            return result

    except Exception as err:
        print(f"❌ Error Saving to database: {err}")
        return None

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

    if (
        event.get("type") == "message"
        and not event.get("subtype")
        and event.get("channel") == TARGET_CHANNEL
        and "thread_ts" in event
        and event["ts"] != event["thread_ts"]
    ):  
        parent_message = get_parent_message(event["thread_ts"])

        if not parent_message:
            raise ValueError("Parent message is required")

        parent_message_id = get_parent_message_id(parent_message)

        if not parent_message_id:
            raise ValueError("Parent message_id not found")

        saving_result = save_slack_response(parent_message_id, event["text"])

        if not saving_result:
            raise ValueError("Fail saving slack reply to database")

        print(f"Saving result: {saving_result}")

if __name__ == "__main__":
    print(f"Listening for Slack replies on port {PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
