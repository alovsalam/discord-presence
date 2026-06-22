import asyncio
import json
import os
import sys
import time
from fastapi import FastAPI
import uvicorn
import websockets

# Initialize FastAPI app for cloud keep-alive services
app = FastAPI()

GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"
# Retrieve the token securely from the environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
GAME_APP_ID = "1159152390754877470"  # Counter-Strike 2 Application ID

@app.get("/")
async def health_check():
    """Endpoint for uptime monitoring services to ping."""
    return {"status": "online", "timestamp": time.time()}

async def send_heartbeat(ws, interval):
    """Periodically sends heartbeats to keep the gateway connection alive."""
    while True:
        await asyncio.sleep(interval / 1000.0)
        heartbeat_payload = {
            "op": 1,  # Opcode 1: Heartbeat
            "d": None
        }
        try:
            await ws.send(json.dumps(heartbeat_payload))
            print("[Gateway] Heartbeat sent.")
        except Exception as e:
            print(f"[Gateway] Failed to send heartbeat: {e}")
            break

async def discord_gateway_loop():
    """Manages the lifetime connection to the Discord Gateway."""
    if not TOKEN:
        print("[Critical] DISCORD_TOKEN environment variable is missing!", file=sys.stderr)
        return

    print("[Gateway] Connecting to Discord Gateway...")
    
    async for ws in websockets.connect(GATEWAY_URL):
        try:
            # 1. Handle Hello Payload (Opcode 10)
            hello_packet = await ws.recv()
            hello_data = json.loads(hello_packet)
            
            if hello_data.get("op") != 10:
                print(f"[Gateway] Unexpected initial opcode: {hello_data.get('op')}")
                continue
                
            heartbeat_interval = hello_data["d"]["heartbeat_interval"]
            print(f"[Gateway] Connected. Heartbeat Interval: {heartbeat_interval}ms")

            # Start the heartbeat loop as a concurrent background task
            heartbeat_task = asyncio.create_task(send_heartbeat(ws, heartbeat_interval))

            # 2. Send Identify Payload (Opcode 2) with Custom Presence
            identify_payload = {
                "op": 2,
                "d": {
                    "token": TOKEN,
                    "capabilities": 125,  # Standard client capabilities flags
                    "properties": {
                        "os": "Windows",
                        "browser": "Discord Client",
                        "device": ""
                    },
                    "presence": {
                        "activities": [{
                            "name": "Counter-Strike 2",
                            "type": 0,  # Type 0 = Playing
                            "application_id": GAME_APP_ID,
                            "timestamps": {
                                "start": int(time.time() * 1000)
                            }
                        }],
                        "status": "online",
                        "since": 0,
                        "afk": False
                    },
                    "compress": False
                }
            }

            await ws.send(json.dumps(identify_payload))
            print("[Gateway] Identify payload sent. Presence updated to Counter-Strike 2.")

            # Keep reading incoming messages to maintain connection vitality
            async for message in ws:
                data = json.loads(message)
                # You can log specific dispatch events here if debugging (e.g., data.get("t"))
                pass

        except websockets.ConnectionClosed:
            print("[Gateway] Connection lost. Attempting reconnect...")
            continue
        except Exception as e:
            print(f"[Gateway] Error encountered: {e}")
            await asyncio.sleep(5)
            continue
        finally:
            # Clean up the heartbeat task on loop reset
            if 'heartbeat_task' in locals():
                heartbeat_task.cancel()

async def main():
    # Start the HTTP server and Gateway client concurrently within the same event loop
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        server.serve(),
        discord_gateway_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
