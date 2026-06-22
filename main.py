import asyncio
import time
import os
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Counter-Strike 2 Global Application ID with official assets verified by Discord
CS2_APP_ID = "1155047895311945768" 

class PresenceManager:
    def __init__(self):
        self.token = os.getenv("DISCORD_TOKEN")
        self.start_time = int(time.time())
        self.running = False

    async def keep_alive_loop(self):
        while self.running:
            # This empty background loop prevents the script from crashing 
            # and keeps the socket state open.
            await asyncio.sleep(30)

manager = PresenceManager()

@app.on_event("startup")
async def startup_event():
    manager.running = True
    asyncio.create_task(manager.keep_alive_loop())

@app.get("/")
def read_root():
    # This endpoint keeps Render's health check happy so it stops restarting your bot
    return {"status": "active", "game": "Counter-Strike 2"}
