import asyncio
import websockets

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZWI3OWMyNC04MGMxLTQ4NjUtOGVmNi0xYzA3YjQ2YTQ5MzIiLCJpYXQiOjE3ODYwMTQ0NzIsImV4cCI6MTc4NjEwMDg3Miwicm9sZSI6ImFkbWluIn0.5HX3QGojMxQukO3ODsn98dNMV3csfWSGT6JlU4JXCP4"

async def main():
    uri = f"ws://localhost:8000/api/v1/ws/live?token={TOKEN}"
    async with websockets.connect(uri) as ws:
        print("Connected. Waiting for a broadcast... (publish an MQTT message now)")
        message = await ws.recv()
        print("Received:", message)

asyncio.run(main())