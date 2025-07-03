import React, { useState, useEffect, useRef, createContext, useContext } from 'react';
import io from 'socket.io-client';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Socket Context
const SocketContext = createContext();

const SocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const newSocket = io(BACKEND_URL, {
      transports: ['websocket', 'polling'],
      upgrade: true,
      rememberUpgrade: true,
    });

    newSocket.on('connect', () => {
      console.log('Connected to server');
      setConnected(true);
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from server');
      setConnected(false);
    });

    newSocket.on('connected', (data) => {
      console.log('Server confirmation:', data.message);
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  return (
    <SocketContext.Provider value={{ socket, connected }}>
      {children}
    </SocketContext.Provider>
  );
};

const useSocket = () => {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
};

// Username Modal Component
const UsernameModal = ({ onSetUsername }) => {
  const [username, setUsername] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (username.trim()) {
      onSetUsername(username.trim());
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 max-w-sm w-full mx-4">
        <h2 className="text-2xl font-bold mb-4 text-center text-gray-800">Enter Your Username</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Your username..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
            autoFocus
          />
          <button
            type="submit"
            className="w-full bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 transition-colors"
            disabled={!username.trim()}
          >
            Join Chat
          </button>
        </form>
      </div>
    </div>
  );
};

// Room Selection Component
const RoomSelection = ({ onJoinRoom, onCreateRoom }) => {
  const [rooms, setRooms] = useState([]);
  const [newRoomName, setNewRoomName] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);

  useEffect(() => {
    fetchRooms();
  }, []);

  const fetchRooms = async () => {
    try {
      const response = await axios.get(`${API}/rooms`);
      setRooms(response.data);
    } catch (error) {
      console.error('Error fetching rooms:', error);
    }
  };

  const handleCreateRoom = async (e) => {
    e.preventDefault();
    if (newRoomName.trim()) {
      try {
        const response = await axios.post(`${API}/rooms?room_name=${encodeURIComponent(newRoomName.trim())}&created_by=user`);
        setRooms([...rooms, response.data]);
        setNewRoomName('');
        setShowCreateForm(false);
        onCreateRoom(response.data);
      } catch (error) {
        console.error('Error creating room:', error);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">💬 Chat Rooms</h1>
          <p className="text-gray-600">Select a room to join or create a new one</p>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-800">Available Rooms</h2>
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
            >
              + Create Room
            </button>
          </div>

          {showCreateForm && (
            <form onSubmit={handleCreateRoom} className="mb-4 p-4 bg-gray-50 rounded-lg">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newRoomName}
                  onChange={(e) => setNewRoomName(e.target.value)}
                  placeholder="Enter room name..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="submit"
                  className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 transition-colors"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="bg-gray-500 text-white px-4 py-2 rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {rooms.length === 0 ? (
              <div className="col-span-full text-center py-8 text-gray-500">
                No rooms available. Create one to get started!
              </div>
            ) : (
              rooms.map((room) => (
                <div
                  key={room.id}
                  className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors cursor-pointer"
                  onClick={() => onJoinRoom(room)}
                >
                  <h3 className="font-semibold text-gray-800 mb-2">{room.name}</h3>
                  <p className="text-sm text-gray-600">
                    Created by {room.created_by}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(room.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Chat Room Component
const ChatRoom = ({ room, username, onLeaveRoom }) => {
  const { socket } = useSocket();
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [typingUsers, setTypingUsers] = useState([]);
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  useEffect(() => {
    if (socket && room) {
      // Join the room
      socket.emit('join_room', {
        username: username,
        room_id: room.id
      });

      // Listen for room joined confirmation
      socket.on('room_joined', (data) => {
        setMessages(data.messages || []);
        setOnlineUsers(data.users || []);
        scrollToBottom();
      });

      // Listen for new messages
      socket.on('new_message', (message) => {
        setMessages(prev => [...prev, message]);
        scrollToBottom();
      });

      // Listen for user joined
      socket.on('user_joined', (data) => {
        setOnlineUsers(data.users || []);
      });

      // Listen for user left
      socket.on('user_left', (data) => {
        setOnlineUsers(data.users || []);
      });

      // Listen for typing indicators
      socket.on('user_typing', (data) => {
        if (data.is_typing) {
          setTypingUsers(prev => [...prev.filter(u => u !== data.username), data.username]);
        } else {
          setTypingUsers(prev => prev.filter(u => u !== data.username));
        }
      });

      return () => {
        socket.off('room_joined');
        socket.off('new_message');
        socket.off('user_joined');
        socket.off('user_left');
        socket.off('user_typing');
      };
    }
  }, [socket, room, username]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (newMessage.trim() && socket) {
      socket.emit('send_message', {
        room_id: room.id,
        message: newMessage.trim()
      });
      setNewMessage('');
      
      // Stop typing indicator
      socket.emit('typing', {
        room_id: room.id,
        is_typing: false
      });
    }
  };

  const handleTyping = (e) => {
    setNewMessage(e.target.value);
    
    if (socket) {
      // Send typing indicator
      socket.emit('typing', {
        room_id: room.id,
        is_typing: true
      });
      
      // Clear previous timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      
      // Set new timeout to stop typing indicator
      typingTimeoutRef.current = setTimeout(() => {
        socket.emit('typing', {
          room_id: room.id,
          is_typing: false
        });
      }, 1000);
    }
  };

  const handleLeaveRoom = () => {
    if (socket) {
      socket.emit('leave_room', { room_id: room.id });
    }
    onLeaveRoom();
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg">
        <div className="p-4 border-b">
          <h2 className="font-semibold text-gray-800 truncate">{room.name}</h2>
          <p className="text-sm text-gray-600">as {username}</p>
        </div>
        
        <div className="p-4">
          <h3 className="font-medium text-gray-700 mb-3">Online Users ({onlineUsers.length})</h3>
          <div className="space-y-2">
            {onlineUsers.map((user, index) => (
              <div key={index} className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm text-gray-700">{user.username}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="absolute bottom-4 left-4 right-4">
          <button
            onClick={handleLeaveRoom}
            className="w-full bg-red-500 text-white py-2 px-4 rounded-lg hover:bg-red-600 transition-colors"
          >
            Leave Room
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.username === username ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.username === username
                    ? 'bg-blue-500 text-white'
                    : 'bg-white text-gray-800'
                }`}
              >
                {message.username !== username && (
                  <p className="text-xs font-medium mb-1 opacity-70">{message.username}</p>
                )}
                <p className="text-sm">{message.message}</p>
                <p className="text-xs mt-1 opacity-70">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
          
          {typingUsers.length > 0 && (
            <div className="flex justify-start">
              <div className="bg-gray-200 text-gray-600 px-4 py-2 rounded-lg text-sm">
                {typingUsers.join(', ')} {typingUsers.length === 1 ? 'is' : 'are'} typing...
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <div className="p-4 border-t bg-white">
          <form onSubmit={handleSendMessage} className="flex space-x-2">
            <input
              type="text"
              value={newMessage}
              onChange={handleTyping}
              placeholder="Type your message..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors"
              disabled={!newMessage.trim()}
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

// Main App Component
const App = () => {
  const [username, setUsername] = useState('');
  const [currentRoom, setCurrentRoom] = useState(null);
  const [appState, setAppState] = useState('username'); // 'username', 'rooms', 'chat'

  const handleSetUsername = (name) => {
    setUsername(name);
    setAppState('rooms');
  };

  const handleJoinRoom = (room) => {
    setCurrentRoom(room);
    setAppState('chat');
  };

  const handleCreateRoom = (room) => {
    setCurrentRoom(room);
    setAppState('chat');
  };

  const handleLeaveRoom = () => {
    setCurrentRoom(null);
    setAppState('rooms');
  };

  return (
    <SocketProvider>
      <div className="App">
        {appState === 'username' && (
          <UsernameModal onSetUsername={handleSetUsername} />
        )}
        
        {appState === 'rooms' && (
          <RoomSelection 
            onJoinRoom={handleJoinRoom}
            onCreateRoom={handleCreateRoom}
          />
        )}
        
        {appState === 'chat' && currentRoom && (
          <ChatRoom
            room={currentRoom}
            username={username}
            onLeaveRoom={handleLeaveRoom}
          />
        )}
      </div>
    </SocketProvider>
  );
};

export default App;