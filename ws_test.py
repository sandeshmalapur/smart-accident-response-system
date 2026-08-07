import asyncio
import websockets

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZWI3OWMyNC04MGMxLTQ4NjUtOGVmNi0xYzA3YjQ2YTQ5MzIiLCJpYXQiOjE3ODYwNzQzNDUsImV4cCI6MTc4NjE2MDc0NSwicm9sZSI6ImFkbWluIn0.nisz1vCE6y78ryWcG6bq0PoQ0STkPcfCNmx1f-_XrY8"

async def main():
    uri = f"ws://localhost:8000/api/v1/ws/live?token={TOKEN}"
    async with websockets.connect(uri) as ws:
        print("Connected. Waiting for a broadcast... (publish an MQTT message now)")
        message = await ws.recv()
        print("Received:", message)

asyncio.run(main())