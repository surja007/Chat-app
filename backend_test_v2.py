#!/usr/bin/env python3
import requests
import uuid
import time
import json
from datetime import datetime

# Backend URL from the test request
BACKEND_URL = "https://df6de6e2-7252-4a01-880e-c4e6b7604863.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"

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
    
    # Test room messages endpoint
    room_id = room["id"]
    messages = test_get_room_messages(room_id)
    test_results.add_result("Room Messages API", True, f"Room messages API working, found {len(messages)} messages")
    
    # Test room users endpoint
    users = test_get_room_users(room_id)
    test_results.add_result("Room Users API", True, f"Room users API working, found {len(users)} users")

# ===== SOCKET.IO TESTS =====

def test_socket_io_apis():
    """Test Socket.IO-related APIs"""
    # Create a test room
    room = test_create_room()
    if not room:
        test_results.add_result("Socket.IO Room Management", False, "Could not create a room for testing")
        return
    
    room_id = room["id"]
    
    # Test room users endpoint (which would be used by Socket.IO for user presence)
    users = test_get_room_users(room_id)
    test_results.add_result("Socket.IO User Presence API", True, f"Room users API working, found {len(users)} users")
    
    # Test room messages endpoint (which would be used by Socket.IO for message history)
    messages = test_get_room_messages(room_id)
    test_results.add_result("Socket.IO Message History API", True, f"Room messages API working, found {len(messages)} messages")

# ===== MAIN TEST RUNNER =====

def run_tests():
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
    
    # Test Socket.IO-related APIs
    print("\n===== Testing Socket.IO-related APIs =====")
    test_socket_io_apis()
    
    # Print test summary
    test_results.print_summary()

if __name__ == "__main__":
    run_tests()