import time
import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect

from dotenv import load_dotenv

load_dotenv()

def load_prompt(file_name):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    prompt_path = os.path.join(dir_path, f'{file_name}.txt')

    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Could not find file: {prompt_path}")
        raise

async def check_number_allowed(to):
    """Check if a number is allowed to be called."""
    try:
        # Uncomment these lines to test numbers. Only add numbers you have permission to call
        # OVERRIDE_NUMBERS = ['+18005551212']
        # if to in OVERRIDE_NUMBERS:
          # return True
        #控制的 Twilio 来电号码
        incoming_numbers = client.incoming_phone_numbers.list(phone_number=to)
        if incoming_numbers:
            return True

        # 验证外拨来电 ID
        outgoing_caller_ids = client.outgoing_caller_ids.list(phone_number=to)
        if outgoing_caller_ids:
            return True

        return False
    except Exception as e:
        print(f"Error checking phone number: {e}")
        return False


# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') # requires OpenAI Realtime API Access
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
NGROK_URL = os.getenv('NGROK_URL')
PORT = int(os.getenv('PORT', 5050))

SYSTEM_MESSAGE = load_prompt('system_prompt')
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

app = FastAPI()

SHOW_TIMING_MATH = False

if not OPENAI_API_KEY:
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
    raise ValueError('Missing Twilio configuration. Please set it in the .env file.')


# async def make_call(phone_number_to_call: str):
#     """Make an outbound call."""
#     if not phone_number_to_call:
#         raise ValueError("Please provide a phone number to call.")

#     is_allowed = await check_number_allowed(phone_number_to_call)
#     if not is_allowed:
#         raise ValueError(f"The number {phone_number_to_call} is not recognized as a valid outgoing number or caller ID.")

#     # Ensure compliance with applicable laws and regulations
#     # All of the rules of TCPA apply even if a call is made by AI.
#     # Do your own diligence for compliance.

#     outbound_twiml = (
#         f'<?xml version="1.0" encoding="UTF-8"?>'
#         f'<Response><Connect><Stream url="wss://{NGROK_URL}/media-stream" /></Connect></Response>'
#     )

#     client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
#     call = client.calls.create(
#         from_=TWILIO_PHONE_NUMBER,
#         to=phone_number_to_call,
#         twiml=outbound_twiml
#     )
#     print(f"Call initiated with SID: {call.sid}")

@app.get("/", response_class=HTMLResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}


# 接电话
@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    response = VoiceResponse()
    # <Say> punctuation to improve text-to-speech flow
    response = VoiceResponse()
    response.say("Ahoy,稍等一下哦，转接中, 转接中……")
    response.pause(length=1)
    response.say("好了，它上线啦！想说啥尽管说吧~")
    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

# 下面是打电话
@app.post("/make-call")
async def make_call(request: Request):
    """Make an outgoing call to the specified phone number."""
    data = await request.json()
    to_phone_number = data.get("to")
    if not to_phone_number:
        return {"error": "Phone number is required"}

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    call = client.calls.create(
        url=f"{NGROK_URL}/outgoing-call",
        to=to_phone_number,
        from_=TWILIO_PHONE_NUMBER
    )
    print(f"Call started with SID: {call.sid}")
    return {"call_sid": call.sid}

@app.api_route("/outgoing-call", methods=["GET", "POST"])
async def handle_outgoing_call(request: Request):
    """Handle outgoing call and return TwiML response to connect to Media Stream."""
    response = VoiceResponse()
    response.say("稍等一下哦，正在召唤全宇宙最聪明的AI语音助理……")
    response.pause(length=1)
    response.say("好了，它上线啦！想说啥尽管说吧~")

    connect = Connect()
    connect.stream(url=f'wss://{request.url.hostname}/media-stream')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Twilio attempting to connect WebSocket...")
    await websocket.accept()
    print("Handshake complete with Twilio 🎉")

    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
        await initialize_session(openai_ws)
        stream_sid = None
        session_id = None


        latest_media_timestamp = 0
        last_assistant_item = None
        mark_queue = []
        response_start_timestamp_twilio = None

        print("Connected to OpenAI Realtime API")
        print("Waiting for Twilio to send audio data...")

        async def receive_from_twilio():
            """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
            nonlocal stream_sid, latest_media_timestamp
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        latest_media_timestamp = int(data['media']['timestamp'])
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print(f"Incoming stream has started {stream_sid}")
                        response_start_timestamp_twilio = None
                        latest_media_timestamp = 0
                        last_assistant_item = None
                    elif data['event'] == 'mark':
                        if mark_queue:
                            mark_queue.pop(0)
            except WebSocketDisconnect:
                print("Client disconnected.")
                if openai_ws.open:
                    await openai_ws.close()

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid, session_id, response_start_timestamp_twilio
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    if response['type'] in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)
                    if response['type'] == 'session.created':
                        session_id = response['session']['id']
                    if response['type'] == 'session.updated':
                        print("Session updated successfully:", response)
                    if response['type'] == 'response.audio.delta' and response.get('delta'):
                        audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                        audio_delta = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": audio_payload
                            }
                        }
                        await websocket.send_json(audio_delta)

                        if response.get("item_id") and response["item_id"] != last_assistant_item:
                            response_start_timestamp_twilio = latest_media_timestamp
                            last_assistant_item = response["item_id"]

                        await send_mark(websocket, stream_sid)

                    # Trigger an interruption. Your use case might work better using `input_audio_buffer.speech_stopped`, or combining the two.
                    # Interrupt handling/AI preemption 清除 Twilio 媒体流缓冲区并发送 OpenAI conversation.item.truncate
                    if response.get('type') == 'input_audio_buffer.speech_started':
                        print("Speech started detected.")
                        if last_assistant_item:
                            print(f"Interrupting response with id: {last_assistant_item}")
                            await handle_speech_started_event()

                    if response['type'] == 'conversation.item.created':
                        print(f"conversation.item.created event: {response}")
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")


        async def handle_speech_started_event():
            """Handle interruption when the caller's speech starts."""
            nonlocal response_start_timestamp_twilio, last_assistant_item
            print("Handling speech started event.")
            if mark_queue and response_start_timestamp_twilio is not None:
                elapsed_time = latest_media_timestamp - response_start_timestamp_twilio
                if SHOW_TIMING_MATH:
                    print(f"Calculating elapsed time for truncation: {latest_media_timestamp} - {response_start_timestamp_twilio} = {elapsed_time}ms")

                if last_assistant_item:
                    if SHOW_TIMING_MATH:
                        print(f"Truncating item with ID: {last_assistant_item}, Truncated at: {elapsed_time}ms")

                    truncate_event = {
                        "type": "conversation.item.truncate",
                        "item_id": last_assistant_item,
                        "content_index": 0,
                        "audio_end_ms": elapsed_time
                    }
                    await openai_ws.send(json.dumps(truncate_event))

                await websocket.send_json({
                    "event": "clear",
                    "streamSid": stream_sid
                })

                mark_queue.clear()
                last_assistant_item = None
                response_start_timestamp_twilio = None

        async def send_mark(connection, stream_sid):
            if stream_sid:
                mark_event = {
                    "event": "mark",
                    "streamSid": stream_sid,
                    "mark": {"name": "responsePart"}
                }
                await connection.send_json(mark_event)
                mark_queue.append('responsePart')

        await asyncio.gather(receive_from_twilio(), send_to_twilio())


async def send_initial_conversation_item(openai_ws):
    """Send initial conversation so AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "您好！我是小赖,受聘於「大赖市調研究中心」進行房地产市場調查。請問您最近有空嗎？我想了解一下您具體的购房想法和需求，看看我能如何進一步協助您。"
                    )
                }
            ]
        }
    }
    await openai_ws.send(json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps({"type": "response.create"}))

#入站和出站音频格式设置为 g711_ulaw 。该格式受 Twilio 和媒体流支持
async def initialize_session(openai_ws):
    """Control initial session Send session update to OpenAI WebSocket."""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

    # Have the AI speak first
    await send_initial_conversation_item(openai_ws)

#python main.py --call=sip:admin@jokerrr.sip.twilio.com
if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Run the Twilio AI voice assistant server.")
    parser.add_argument('--call', required=True, help="The phone number to call, e.g., '--call=+18005551212'")
    args = parser.parse_args()

    phone_number = args.call

    print(
        'Our recommendation is to always disclose the use of AI for outbound or inbound calls.\n'
        'Reminder: All of the rules of TCPA apply even if a call is made by AI.\n'
        'Check with your counsel for legal and compliance advice.'
    )

    #to_phone_number = input("Please enter the phone number to call: ")
    to_phone_number = phone_number
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    try:
        call = client.calls.create(
            url=f"{NGROK_URL}/outgoing-call",
            to=to_phone_number,
            from_=TWILIO_PHONE_NUMBER
        )
        print(f"Call initiated with SID: {call.sid}")
    except Exception as e:
        print(f"Error initiating call: {e}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
