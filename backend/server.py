from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import socketio
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)

# Create the main app
app = FastAPI()

# Create Socket.IO ASGI app
socket_app = socketio.ASGIApp(sio, app)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Data Models
class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    room_id: str
    username: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Room(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    room_id: Optional[str] = None
    socket_id: Optional[str] = None
    is_online: bool = True
    last_seen: datetime = Field(default_factory=datetime.utcnow)

# Store active users and rooms in memory for quick access
active_users = {}
room_users = {}

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Chat App API"}

@api_router.get("/rooms", response_model=List[Room])
async def get_rooms():
    """Get all available chat rooms"""
    rooms = await db.rooms.find().to_list(1000)
    return [Room(**room) for room in rooms]

@api_router.post("/rooms", response_model=Room)
async def create_room(room_name: str, created_by: str):
    """Create a new chat room"""
    room = Room(name=room_name, created_by=created_by)
    await db.rooms.insert_one(room.dict())
    return room

@api_router.get("/rooms/{room_id}/messages", response_model=List[Message])
async def get_room_messages(room_id: str, limit: int = 50):
    """Get last N messages from a room"""
    messages = await db.messages.find(
        {"room_id": room_id}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Reverse to get chronological order
    messages.reverse()
    return [Message(**msg) for msg in messages]

@api_router.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str):
    """Get online users in a room"""
    return {"users": room_users.get(room_id, [])}

# Socket.IO Event Handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    print(f"Client {sid} connected")
    await sio.emit('connected', {'message': 'Connected to server'}, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    print(f"Client {sid} disconnected")
    
    # Remove user from active users and room
    if sid in active_users:
        user_info = active_users[sid]
        username = user_info['username']
        room_id = user_info.get('room_id')
        
        if room_id and room_id in room_users:
            room_users[room_id] = [u for u in room_users[room_id] if u['username'] != username]
            
            # Notify other users in the room
            await sio.emit('user_left', {
                'username': username,
                'users': room_users[room_id]
            }, room=room_id)
        
        del active_users[sid]

@sio.event
async def join_room(sid, data):
    """Handle user joining a room"""
    try:
        username = data['username']
        room_id = data['room_id']
        
        # Store user information
        active_users[sid] = {
            'username': username,
            'room_id': room_id,
            'socket_id': sid
        }
        
        # Add user to Socket.IO room
        await sio.enter_room(sid, room_id)
        
        # Add user to room users list
        if room_id not in room_users:
            room_users[room_id] = []
        
        # Check if user is already in the room
        user_exists = any(u['username'] == username for u in room_users[room_id])
        if not user_exists:
            room_users[room_id].append({
                'username': username,
                'socket_id': sid
            })
        
        # Get room messages
        messages = await get_room_messages(room_id, 50)
        
        # Send room data to the joining user
        await sio.emit('room_joined', {
            'room_id': room_id,
            'messages': [msg.dict() for msg in messages],
            'users': room_users[room_id]
        }, room=sid)
        
        # Notify other users in the room
        await sio.emit('user_joined', {
            'username': username,
            'users': room_users[room_id]
        }, room=room_id)
        
    except Exception as e:
        print(f"Error joining room: {e}")
        await sio.emit('error', {'message': 'Failed to join room'}, room=sid)

@sio.event
async def leave_room(sid, data):
    """Handle user leaving a room"""
    try:
        room_id = data['room_id']
        
        if sid in active_users:
            username = active_users[sid]['username']
            
            # Remove from Socket.IO room
            await sio.leave_room(sid, room_id)
            
            # Remove from room users list
            if room_id in room_users:
                room_users[room_id] = [u for u in room_users[room_id] if u['username'] != username]
                
                # Notify other users
                await sio.emit('user_left', {
                    'username': username,
                    'users': room_users[room_id]
                }, room=room_id)
            
            # Update active user info
            active_users[sid]['room_id'] = None
            
    except Exception as e:
        print(f"Error leaving room: {e}")

@sio.event
async def send_message(sid, data):
    """Handle sending a message"""
    try:
        room_id = data['room_id']
        message_text = data['message']
        
        if sid in active_users:
            username = active_users[sid]['username']
            
            # Create message object
            message = Message(
                room_id=room_id,
                username=username,
                message=message_text
            )
            
            # Save to database
            await db.messages.insert_one(message.dict())
            
            # Broadcast to all users in the room
            await sio.emit('new_message', message.dict(), room=room_id)
            
    except Exception as e:
        print(f"Error sending message: {e}")
        await sio.emit('error', {'message': 'Failed to send message'}, room=sid)

@sio.event
async def typing(sid, data):
    """Handle typing indicator"""
    try:
        room_id = data['room_id']
        is_typing = data['is_typing']
        
        if sid in active_users:
            username = active_users[sid]['username']
            
            # Broadcast typing status to other users in the room
            await sio.emit('user_typing', {
                'username': username,
                'is_typing': is_typing
            }, room=room_id, skip_sid=sid)
            
    except Exception as e:
        print(f"Error handling typing: {e}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Mount the Socket.IO app
app.mount("/", socket_app)