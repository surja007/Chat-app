#!/usr/bin/env python3
import requests
import socketio
import asyncio
import uuid
import time
import json
from datetime import datetime

# Backend URL from the test request
BACKEND_URL = "https://df6de6e2-7252-4a01-880e-c4e6b7604863.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"
SOCKET_URL = BACKEND_URL

class TestResults:
    def __init__(self):
        self.results = {}
        self.passed = 0
        self.failed = 0
        self.total = 0
    
    def add_result(self, test_name, passed, message=""):
        self.results[test_name] = {
            "passed": passed,
            "message": message
        }
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.total += 1
    
    def print_summary(self):
        print("\n===== TEST SUMMARY =====")
        print(f"Total Tests: {self.total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print("========================\n")
        
        print("Detailed Results:")
        for test_name, result in self.results.items():
            status = "✅ PASSED" if result["passed"] else "❌ FAILED"
            print(f"{status} - {test_name}")
            if result["message"]:
                print(f"  Message: {result['message']}")
        
        print("\n========================")

# Initialize test results
test_results = TestResults()

# ===== API ENDPOINT TESTS =====

def test_api_root():
    """Test the API root endpoint"""
    try:
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200 and "message" in response.json():
            test_results.add_result("API Root Endpoint", True, "API root endpoint is working")
        else:
            test_results.add_result("API Root Endpoint", False, f"API root endpoint returned unexpected response: {response.text}")
    except Exception as e:
        test_results.add_result("API Root Endpoint", False, f"Error testing API root endpoint: {str(e)}")

def test_get_rooms():
    """Test getting all chat rooms"""
    try:
        response = requests.get(f"{API_URL}/rooms")
        if response.status_code == 200:
            rooms = response.json()
            test_results.add_result("GET /api/rooms", True, f"Successfully retrieved {len(rooms)} rooms")
            return rooms
        else:
            test_results.add_result("GET /api/rooms", False, f"Failed to get rooms: {response.text}")
            return []
    except Exception as e:
        test_results.add_result("GET /api/rooms", False, f"Error getting rooms: {str(e)}")
        return []

def test_create_room():
    """Test creating a new chat room"""
    try:
        room_name = f"Test Room {uuid.uuid4()}"
        created_by = f"Tester-{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{API_URL}/rooms", params={"room_name": room_name, "created_by": created_by})
        
        if response.status_code == 200:
            room = response.json()
            if room["name"] == room_name and room["created_by"] == created_by:
                test_results.add_result("POST /api/rooms", True, f"Successfully created room: {room_name}")
                return room
            else:
                test_results.add_result("POST /api/rooms", False, f"Room created but data mismatch: {room}")
                return room
        else:
            test_results.add_result("POST /api/rooms", False, f"Failed to create room: {response.text}")
            return None
    except Exception as e:
        test_results.add_result("POST /api/rooms", False, f"Error creating room: {str(e)}")
        return None

def test_get_room_messages(room_id):
    """Test getting messages from a room"""
    try:
        response = requests.get(f"{API_URL}/rooms/{room_id}/messages")
        
        if response.status_code == 200:
            messages = response.json()
            test_results.add_result("GET /api/rooms/{room_id}/messages", True, f"Successfully retrieved {len(messages)} messages")
            return messages
        else:
            test_results.add_result("GET /api/rooms/{room_id}/messages", False, f"Failed to get messages: {response.text}")
            return []
    except Exception as e:
        test_results.add_result("GET /api/rooms/{room_id}/messages", False, f"Error getting messages: {str(e)}")
        return []

def test_get_room_users(room_id):
    """Test getting online users in a room"""
    try:
        response = requests.get(f"{API_URL}/rooms/{room_id}/users")
        
        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])
            test_results.add_result("GET /api/rooms/{room_id}/users", True, f"Successfully retrieved {len(users)} online users")
            return users
        else:
            test_results.add_result("GET /api/rooms/{room_id}/users", False, f"Failed to get users: {response.text}")
            return []
    except Exception as e:
        test_results.add_result("GET /api/rooms/{room_id}/users", False, f"Error getting users: {str(e)}")
        return []

# ===== SOCKET.IO TESTS =====

async def test_socketio():
    """Test all Socket.IO functionality"""
    try:
        # Create two socket clients to simulate different users
        sio1 = socketio.AsyncClient(logger=True)
        sio2 = socketio.AsyncClient(logger=True)
        
        # Track events received
        received_events = {
            "sio1": {},
            "sio2": {}
        }
        
        # Event handlers for first client
        @sio1.event
        async def connected(data):
            print(f"SIO1 connected: {data}")
            received_events["sio1"]["connected"] = data
        
        @sio1.event
        async def room_joined(data):
            print(f"SIO1 room_joined: {data}")
            received_events["sio1"]["room_joined"] = data
        
        @sio1.event
        async def user_joined(data):
            print(f"SIO1 user_joined: {data}")
            received_events["sio1"]["user_joined"] = data
        
        @sio1.event
        async def new_message(data):
            print(f"SIO1 new_message: {data}")
            received_events["sio1"]["new_message"] = data
        
        @sio1.event
        async def user_typing(data):
            print(f"SIO1 user_typing: {data}")
            received_events["sio1"]["user_typing"] = data
        
        @sio1.event
        async def user_left(data):
            print(f"SIO1 user_left: {data}")
            received_events["sio1"]["user_left"] = data
        
        # Event handlers for second client
        @sio2.event
        async def connected(data):
            print(f"SIO2 connected: {data}")
            received_events["sio2"]["connected"] = data
        
        @sio2.event
        async def room_joined(data):
            print(f"SIO2 room_joined: {data}")
            received_events["sio2"]["room_joined"] = data
        
        @sio2.event
        async def user_joined(data):
            print(f"SIO2 user_joined: {data}")
            received_events["sio2"]["user_joined"] = data
        
        @sio2.event
        async def new_message(data):
            print(f"SIO2 new_message: {data}")
            received_events["sio2"]["new_message"] = data
        
        @sio2.event
        async def user_typing(data):
            print(f"SIO2 user_typing: {data}")
            received_events["sio2"]["user_typing"] = data
        
        @sio2.event
        async def user_left(data):
            print(f"SIO2 user_left: {data}")
            received_events["sio2"]["user_left"] = data
        
        # Connect both clients
        await sio1.connect(SOCKET_URL)
        await sio2.connect(SOCKET_URL)
        
        # Wait for connections to establish
        await asyncio.sleep(1)
        
        # Test connection
        if "connected" in received_events["sio1"] and "connected" in received_events["sio2"]:
            test_results.add_result("Socket.IO Connection", True, "Both clients connected successfully")
        else:
            test_results.add_result("Socket.IO Connection", False, "One or both clients failed to connect")
            return
        
        # Create a test room
        room = test_create_room()
        if not room:
            test_results.add_result("Socket.IO Room Management", False, "Could not create a room for testing")
            return
        
        room_id = room["id"]
        
        # Test joining room
        username1 = f"User1-{uuid.uuid4().hex[:6]}"
        await sio1.emit("join_room", {"username": username1, "room_id": room_id})
        
        # Wait for join event
        await asyncio.sleep(1)
        
        if "room_joined" in received_events["sio1"]:
            test_results.add_result("Socket.IO Join Room (First User)", True, f"User {username1} joined room successfully")
        else:
            test_results.add_result("Socket.IO Join Room (First User)", False, "First user failed to join room")
            return
        
        # Second user joins
        username2 = f"User2-{uuid.uuid4().hex[:6]}"
        await sio2.emit("join_room", {"username": username2, "room_id": room_id})
        
        # Wait for join events
        await asyncio.sleep(1)
        
        if "room_joined" in received_events["sio2"] and "user_joined" in received_events["sio1"]:
            test_results.add_result("Socket.IO Join Room (Second User)", True, f"User {username2} joined room successfully")
        else:
            test_results.add_result("Socket.IO Join Room (Second User)", False, "Second user failed to join room or notification failed")
        
        # Test user presence
        users = test_get_room_users(room_id)
        if len(users) >= 2:
            test_results.add_result("Socket.IO User Presence", True, f"Found {len(users)} users in room")
        else:
            test_results.add_result("Socket.IO User Presence", False, f"Expected at least 2 users, found {len(users)}")
        
        # Test sending message
        test_message = f"Test message {uuid.uuid4().hex[:8]}"
        await sio1.emit("send_message", {"room_id": room_id, "message": test_message})
        
        # Wait for message to be received
        await asyncio.sleep(1)
        
        if "new_message" in received_events["sio2"]:
            received_msg = received_events["sio2"]["new_message"]
            if received_msg.get("message") == test_message and received_msg.get("username") == username1:
                test_results.add_result("Socket.IO Message Broadcasting", True, "Message was broadcast correctly")
            else:
                test_results.add_result("Socket.IO Message Broadcasting", False, f"Message mismatch: {received_msg}")
        else:
            test_results.add_result("Socket.IO Message Broadcasting", False, "Message was not received by other user")
        
        # Test message persistence
        messages = test_get_room_messages(room_id)
        message_found = any(msg.get("message") == test_message for msg in messages)
        if message_found:
            test_results.add_result("Socket.IO Message Persistence", True, "Message was stored in database")
        else:
            test_results.add_result("Socket.IO Message Persistence", False, "Message was not found in database")
        
        # Test typing indicator
        await sio1.emit("typing", {"room_id": room_id, "is_typing": True})
        
        # Wait for typing event
        await asyncio.sleep(1)
        
        if "user_typing" in received_events["sio2"]:
            typing_data = received_events["sio2"]["user_typing"]
            if typing_data.get("username") == username1 and typing_data.get("is_typing") is True:
                test_results.add_result("Socket.IO Typing Indicator", True, "Typing indicator was broadcast correctly")
            else:
                test_results.add_result("Socket.IO Typing Indicator", False, f"Typing data mismatch: {typing_data}")
        else:
            test_results.add_result("Socket.IO Typing Indicator", False, "Typing indicator was not received")
        
        # Test leaving room
        await sio1.emit("leave_room", {"room_id": room_id})
        
        # Wait for leave event
        await asyncio.sleep(1)
        
        if "user_left" in received_events["sio2"]:
            left_data = received_events["sio2"]["user_left"]
            if left_data.get("username") == username1:
                test_results.add_result("Socket.IO Leave Room", True, "User left room successfully")
            else:
                test_results.add_result("Socket.IO Leave Room", False, f"User left data mismatch: {left_data}")
        else:
            test_results.add_result("Socket.IO Leave Room", False, "User left event was not received")
        
        # Test disconnect
        await sio1.disconnect()
        await sio2.disconnect()
        test_results.add_result("Socket.IO Disconnect", True, "Clients disconnected successfully")
        
    except Exception as e:
        test_results.add_result("Socket.IO Tests", False, f"Error in Socket.IO tests: {str(e)}")

# ===== DATABASE TESTS =====

def test_database_operations():
    """Test database operations through API endpoints"""
    # Create a room
    room = test_create_room()
    if not room:
        test_results.add_result("Database Room Creation", False, "Failed to create room")
        return
    
    # Verify room exists in the list
    rooms = test_get_rooms()
    room_exists = any(r.get("id") == room["id"] for r in rooms)
    
    if room_exists:
        test_results.add_result("Database Room Retrieval", True, "Room was successfully stored and retrieved")
    else:
        test_results.add_result("Database Room Retrieval", False, "Created room was not found in room list")

# ===== MAIN TEST RUNNER =====

async def run_tests():
    """Run all tests"""
    print("Starting backend tests...")
    
    # Test API endpoints
    print("\n===== Testing API Endpoints =====")
    test_api_root()
    test_get_rooms()
    test_create_room()
    
    # Test database operations
    print("\n===== Testing Database Operations =====")
    test_database_operations()
    
    # Test Socket.IO functionality
    print("\n===== Testing Socket.IO Functionality =====")
    await test_socketio()
    
    # Print test summary
    test_results.print_summary()

if __name__ == "__main__":
    asyncio.run(run_tests())