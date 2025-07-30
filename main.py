import os
import json
import time
import hmac
import hashlib
import uvicorn
import requests
from fastapi import FastAPI, HTTPException, Request, Header
from dotenv import load_dotenv

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


# def get_id_from_message(parent):
#     try:
#         conn = pool.get_connection()
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute("SELECT MAX(id) AS max_id FROM messages WHERE content = %s", (parent,))
#         parent_id = cursor.fetchone()  
#         cursor.close()
#         conn.close()
#         return parent_id
#     except mysql.connector.Error as err:
#         print(f"❌ Database error: {err}")
#         return None

# def save_slack_reply_to_database(message_id, reply_content, reply_at):
#     try:
#         conn = pool.get_connection()
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute(
#             'INSERT INTO replies (message_id, reply_content, reply_at) VALUES (%s, %s, %s)',
#             (message_id, reply_content, reply_at)
#         )
#         conn.commit()  # Important: commit the insert
#         inserted_id = cursor.lastrowid
#         cursor.close()
#         conn.close()
#         return inserted_id
#     except mysql.connector.Error as err:
#         print(f"❌ Database error: {err}")
#         return None

def get_parent_message(timestamp: str):
    try:
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
        }

        response = requests.post(url = f"{SLACK_REFLIES_API_URL}?channel={TARGET_CHANNEL}&ts={timestamp}&limit=1&pretty=1", headers = headers)

        if response.get('messages'):
            messages = response.get('messages')
            parent_message = messages[0]["text"]
            print(f"Parent message of {timestamp}: {parent_message}")

    except Exception as e:
        print(f"Error getting parent messages from slack: {e}")

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

    # print(f"Data from slack event: {data}")
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
        get_parent_message(event["thread_ts"])

    #     try:
    #         parent_headers = {
    #             "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
    #         }
    #         parent_message = requests.post(url=parent_url, headers=headers)
    #         parent_message_list = parent_message["messages"]
    #         parent = parent_message_list[0]["text"] 
    #         print(f"parent message content: {parent}")

    #         parent_id = get_id_from_message(parent)

    #         current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    #         inserted_id = save_slack_reply_to_database(parent_id, event.get("text"), current_time)
    #         print(f"inserted_id= {inserted_id}")
            
    #     except Exception as e:
    #         print(f"Error forwarding reply: {e}")

    # return Response(status_code=200)

if __name__ == "__main__":
    print(f"Listening for Slack replies on port {PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
