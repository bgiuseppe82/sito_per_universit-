import React, { useState, useEffect, useRef, createContext, useContext } from 'react';
import './App.css';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import './i18n';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sessionToken, setSessionToken] = useState(localStorage.getItem('sessionToken'));
  const { i18n } = useTranslation();

  useEffect(() => {
    // Check if returning from auth
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id') || window.location.hash.split('session_id=')[1];
    
    if (sessionId) {
      setSessionToken(sessionId);
      localStorage.setItem('sessionToken', sessionId);
      fetchProfile(sessionId);
    } else if (sessionToken) {
      fetchProfile(sessionToken);
    } else {
      setLoading(false);
    }
  }, [sessionToken]);

  const fetchProfile = async (token) => {
    try {
      const response = await axios.get(`${API}/auth/profile`, {
        headers: { 'X-Session-ID': token }
      });
      
      const userData = response.data;
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
      
      // Set language preference
      if (userData.preferred_language) {
        i18n.changeLanguage(userData.preferred_language);
      }
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      localStorage.removeItem('sessionToken');
      localStorage.removeItem('user');
      setSessionToken(null);
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    const currentUrl = window.location.origin;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(currentUrl)}`;
  };

  const logout = () => {
    localStorage.removeItem('sessionToken');
    localStorage.removeItem('user');
    setUser(null);
    setSessionToken(null);
  };

  const updateUserLanguage = async (language) => {
    try {
      await axios.put(`${API}/user/language`, { language }, {
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
      
      // Update local user data
      const updatedUser = { ...user, preferred_language: language };
      setUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
      
      // Change UI language
      i18n.changeLanguage(language);
    } catch (error) {
      console.error('Failed to update language:', error);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, sessionToken, updateUserLanguage }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Audio Recording Hook
const useAudioRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioData, setAudioData] = useState(null);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);

  const startRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      const chunks = [];
      mediaRecorder.ondataavailable = (event) => {
        chunks.push(event.data);
      };
      
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onload = () => {
          setAudioData(reader.result.split(',')[1]); // Remove data URL prefix
        };
        reader.readAsDataURL(blob);
      };
      
      mediaRecorder.start();
      setIsRecording(true);
      setDuration(0);
      
      // Start duration timer
      intervalRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
      
    } catch (err) {
      setError('Failed to access microphone. Please check permissions.');
      console.error('Recording error:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    setIsRecording(false);
  };

  const resetRecording = () => {
    setAudioData(null);
    setDuration(0);
    setError(null);
  };

  return {
    isRecording,
    audioData,
    duration,
    error,
    startRecording,
    stopRecording,
    resetRecording
  };
};

// Components
const Header = () => {
  const { user, login, logout } = useAuth();

  return (
    <header className="bg-blue-600 text-white p-4 shadow-lg">
      <div className="container mx-auto flex justify-between items-center">
        <h1 className="text-2xl font-bold">SmartNotes</h1>
        <div className="flex items-center space-x-4">
          {user ? (
            <>
              <span className="text-sm">Welcome, {user.name}</span>
              <button
                onClick={logout}
                className="bg-blue-500 hover:bg-blue-700 px-4 py-2 rounded text-sm"
              >
                Logout
              </button>
            </>
          ) : (
            <button
              onClick={login}
              className="bg-blue-500 hover:bg-blue-700 px-4 py-2 rounded text-sm"
            >
              Login
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

const LoadingSpinner = () => (
  <div className="flex justify-center items-center h-screen">
    <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
  </div>
);

const RecordingControls = ({ onRecordingComplete }) => {
  const { isRecording, audioData, duration, error, startRecording, stopRecording, resetRecording } = useAudioRecorder();
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState('');
  const [notes, setNotes] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const { sessionToken } = useAuth();

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSaveRecording = async () => {
    if (!audioData || !title.trim()) return;
    
    setIsUploading(true);
    try {
      const response = await axios.post(`${API}/recordings`, {
        title: title.trim(),
        audio_data: audioData,
        tags: tags.split(',').map(tag => tag.trim()).filter(Boolean),
        notes: notes.trim(),
        duration: duration
      }, {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      onRecordingComplete(response.data);
      setTitle('');
      setTags('');
      setNotes('');
      resetRecording();
    } catch (error) {
      console.error('Failed to save recording:', error);
      alert('Failed to save recording. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Record New Lesson</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      <div className="flex items-center justify-center space-x-4 mb-6">
        <div className="text-2xl font-mono">{formatDuration(duration)}</div>
        
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={audioData}
            className="bg-red-500 hover:bg-red-600 disabled:bg-gray-300 text-white p-4 rounded-full transition-colors"
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
            </svg>
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="bg-gray-500 hover:bg-gray-600 text-white p-4 rounded-full transition-colors"
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 012 0v6a1 1 0 11-2 0V7zm4 0a1 1 0 012 0v6a1 1 0 11-2 0V7z" clipRule="evenodd" />
            </svg>
          </button>
        )}
        
        {audioData && (
          <button
            onClick={resetRecording}
            className="bg-gray-400 hover:bg-gray-500 text-white p-2 rounded"
          >
            Reset
          </button>
        )}
      </div>
      
      {audioData && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter lesson title..."
              className="w-full p-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tags (comma-separated)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="physics, lecture, chapter-1"
              className="w-full p-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any additional notes..."
              className="w-full p-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows="3"
            />
          </div>
          
          <button
            onClick={handleSaveRecording}
            disabled={!title.trim() || isUploading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white py-2 px-4 rounded font-medium transition-colors"
          >
            {isUploading ? 'Saving...' : 'Save Recording'}
          </button>
        </div>
      )}
    </div>
  );
};

const RecordingsList = ({ recordings, onRecordingUpdate }) => {
  const { sessionToken } = useAuth();
  const [processing, setProcessing] = useState({});

  const handleProcess = async (recordingId, type) => {
    setProcessing(prev => ({ ...prev, [recordingId]: type }));
    
    try {
      await axios.post(`${API}/recordings/${recordingId}/process`, {
        recording_id: recordingId,
        type: type
      }, {
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
      
      // Poll for completion
      const pollInterval = setInterval(async () => {
        try {
          const response = await axios.get(`${API}/recordings/${recordingId}`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
          });
          
          if (response.data.status === 'completed') {
            clearInterval(pollInterval);
            setProcessing(prev => ({ ...prev, [recordingId]: null }));
            onRecordingUpdate();
          }
        } catch (error) {
          clearInterval(pollInterval);
          setProcessing(prev => ({ ...prev, [recordingId]: null }));
        }
      }, 2000);
      
    } catch (error) {
      console.error('Processing failed:', error);
      setProcessing(prev => ({ ...prev, [recordingId]: null }));
    }
  };

  const handleDelete = async (recordingId) => {
    if (!window.confirm('Are you sure you want to delete this recording?')) return;
    
    try {
      await axios.delete(`${API}/recordings/${recordingId}`, {
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
      onRecordingUpdate();
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Your Recordings</h2>
      
      {recordings.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No recordings yet. Record your first lesson above!
        </div>
      ) : (
        recordings.map(recording => (
          <div key={recording.id} className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-medium">{recording.title}</h3>
                <p className="text-sm text-gray-600">{formatDate(recording.created_at)}</p>
                {recording.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {recording.tags.map((tag, index) => (
                      <span key={index} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              
              <button
                onClick={() => handleDelete(recording.id)}
                className="text-red-500 hover:text-red-700 p-1"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9zM4 5a2 2 0 012-2h8a2 2 0 012 2v10a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 012 0v6a1 1 0 11-2 0V9zm4 0a1 1 0 012 0v6a1 1 0 11-2 0V9z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
            
            {recording.notes && (
              <div className="mb-4 p-3 bg-gray-50 rounded">
                <p className="text-sm text-gray-700">{recording.notes}</p>
              </div>
            )}
            
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleProcess(recording.id, 'full')}
                  disabled={processing[recording.id] === 'full'}
                  className="bg-green-500 hover:bg-green-600 disabled:bg-gray-300 text-white px-4 py-2 rounded text-sm"
                >
                  {processing[recording.id] === 'full' ? 'Processing...' : 'Full Transcript'}
                </button>
                
                <button
                  onClick={() => handleProcess(recording.id, 'summary')}
                  disabled={processing[recording.id] === 'summary'}
                  className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white px-4 py-2 rounded text-sm"
                >
                  {processing[recording.id] === 'summary' ? 'Processing...' : 'Summary'}
                </button>
                
                <button
                  onClick={() => handleProcess(recording.id, 'chapters')}
                  disabled={processing[recording.id] === 'chapters'}
                  className="bg-purple-500 hover:bg-purple-600 disabled:bg-gray-300 text-white px-4 py-2 rounded text-sm"
                >
                  {processing[recording.id] === 'chapters' ? 'Processing...' : 'Chapters'}
                </button>
              </div>
              
              {recording.transcript && (
                <div className="bg-gray-50 p-4 rounded">
                  <h4 className="font-medium mb-2">Transcript:</h4>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{recording.transcript}</p>
                </div>
              )}
              
              {recording.summary && (
                <div className="bg-blue-50 p-4 rounded">
                  <h4 className="font-medium mb-2">Summary:</h4>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{recording.summary}</p>
                </div>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
};

const Dashboard = () => {
  const { user } = useAuth();
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const { sessionToken } = useAuth();

  const fetchRecordings = async () => {
    try {
      const response = await axios.get(`${API}/recordings`, {
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
      setRecordings(response.data);
    } catch (error) {
      console.error('Failed to fetch recordings:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (sessionToken) {
      fetchRecordings();
    }
  }, [sessionToken]);

  const handleRecordingComplete = (newRecording) => {
    setRecordings(prev => [newRecording, ...prev]);
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome to SmartNotes</h1>
        <p className="text-gray-600">Record your lessons and get AI-powered transcripts and summaries</p>
      </div>
      
      <RecordingControls onRecordingComplete={handleRecordingComplete} />
      <RecordingsList recordings={recordings} onRecordingUpdate={fetchRecordings} />
    </div>
  );
};

const LoginPrompt = () => {
  const { login } = useAuth();
  
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">SmartNotes</h1>
          <p className="text-gray-600 mb-8">AI-powered lesson transcription and summarization for students</p>
          
          <div className="space-y-4 mb-8">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-100 p-2 rounded-full">
                <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                </svg>
              </div>
              <span className="text-sm">Record lessons with one tap</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="bg-green-100 p-2 rounded-full">
                <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" clipRule="evenodd" />
                </svg>
              </div>
              <span className="text-sm">AI transcription & summarization</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="bg-purple-100 p-2 rounded-full">
                <svg className="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </div>
              <span className="text-sm">Export & share notes</span>
            </div>
          </div>
          
          <button
            onClick={login}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
          >
            Get Started
          </button>
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <div className="App min-h-screen bg-gray-50">
        <AuthContent />
      </div>
    </AuthProvider>
  );
}

const AuthContent = () => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <LoadingSpinner />;
  }
  
  return (
    <>
      {user ? (
        <>
          <Header />
          <Dashboard />
        </>
      ) : (
        <LoginPrompt />
      )}
    </>
  );
};

export default App;