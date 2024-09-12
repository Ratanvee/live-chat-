from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from database import ChatMessage, get_db
import json

app = FastAPI()

# Store message in the database
def store_message(db: Session, sender: str, message: str, receiver: str = None):
    timestamp = datetime.now()
    db_message = ChatMessage(sender=sender, message=message, receiver=receiver, timestamp=timestamp)
    db.add(db_message)
    db.commit()

# Retrieve chat history from the database
def get_chat_history(db: Session, limit: int = 50):
    return db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(limit).all()

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

    async def send_message_to_client(self, target_client_id: str, message: str):
        if target_client_id in self.active_connections:
            websocket = self.active_connections[target_client_id]
            await websocket.send_text(message)

manager = ConnectionManager()

@app.get("/")
async def get():
    with open("templates/index.html") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, db: Session = Depends(get_db)):
    await manager.connect(websocket, client_id)
    try:
        # Send chat history to the client
        chat_history = get_chat_history(db)
        for msg in reversed(chat_history):
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            data = {
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": timestamp
            }
            await manager.send_personal_message(json.dumps(data), websocket)

        while True:
            data = await websocket.receive_text()
            timestamp = datetime.now().strftime("%H:%M:%S")

            parsed_data = json.loads(data)
            message = parsed_data["message"]
            receiver = parsed_data.get("receiver")  # Get the receiver if provided

            # Prepare message data
            message_data = {
                "sender": client_id,
                "message": message,
                "timestamp": timestamp
            }

            # If there's a receiver, send the message to that specific client
            if receiver:
                await manager.send_message_to_client(receiver, json.dumps(message_data))
            else:
                # Broadcast the message to everyone if no receiver is specified
                await manager.broadcast(json.dumps(message_data))

            # Store the message in the database (with or without a receiver)
            store_message(db, client_id, message, receiver)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
