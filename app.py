from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import SessionLocal, ChatMessage
import datetime

app = FastAPI()

# A manager to handle WebSocket connections
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
        else:
            print(f"Client {target_client_id} not found.")

manager = ConnectionManager()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Store message in database
async def store_message(db: Session, sender: str, message: str, receiver: str = None):
    db_message = ChatMessage(sender=sender, message=message, receiver=receiver)
    db.add(db_message)
    db.commit()

# Retrieve chat history from the database
def get_chat_history(db: Session, limit: int = 50):
    return db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(limit).all()

@app.get("/")
async def get():
    with open("templates/index.html") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, db: Session = Depends(get_db)):
    await manager.connect(websocket, client_id)
    try:
        # Send chat history when the client connects
        chat_history = get_chat_history(db)
        for msg in reversed(chat_history):
            if msg.receiver:
                await manager.send_message_to_client(msg.receiver, f"[History] {msg.sender} to {msg.receiver}: {msg.message}")
            else:
                await manager.send_personal_message(f"[History] {msg.sender}: {msg.message}", websocket)
        
        while True:
            data = await websocket.receive_text()

            if ":" in data:
                target_client_id, message = data.split(":", 1)
                await manager.send_message_to_client(target_client_id.strip(), f"Message from {client_id}: {message.strip()}")
                await store_message(db, client_id, message.strip(), target_client_id.strip())  # Save message
            else:
                await manager.broadcast(f"Client {client_id} says: {data}")
                await store_message(db, client_id, data)  # Save broadcast message
    except WebSocketDisconnect:
        manager.disconnect(client_id)



if __name__ == '__main__':
    import uvicorn
    # uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
    port = int(os.getenv("PORT", 8000))  # Use PORT env variable, default to 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
