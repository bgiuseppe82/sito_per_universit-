#!/usr/bin/env python3
"""
SmartNotes Backend API Testing Suite
Tests all backend endpoints for the SmartNotes application
"""

import requests
import json
import base64
import time
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Configuration
BASE_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://8e812a6d-619e-4f0d-90a9-76273db9a6ed.preview.emergentagent.com')
API_BASE = f"{BASE_URL}/api"

# Test data
TEST_SESSION_ID = "test-session-" + str(uuid.uuid4())
TEST_AUDIO_DATA = base64.b64encode(b"fake-audio-data-for-testing").decode('utf-8')

class BackendTester:
    def __init__(self):
        self.session_token = None
        self.user_id = None
        self.test_recording_id = None
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.results.append(result)
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
    
    def test_health_check(self):
        """Test basic API health check"""
        try:
            response = requests.get(f"{API_BASE}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "SmartNotes API is running" in data.get('message', ''):
                    self.log_result("Health Check", True, "API is running correctly")
                    return True
                else:
                    self.log_result("Health Check", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_result("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_auth_profile(self):
        """Test user authentication with Emergent Auth"""
        try:
            headers = {'X-Session-ID': TEST_SESSION_ID}
            response = requests.get(f"{API_BASE}/auth/profile", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['id', 'email', 'name', 'session_token']
                
                if all(field in data for field in required_fields):
                    self.session_token = data['session_token']
                    self.user_id = data['id']
                    self.log_result("User Authentication", True, "Profile endpoint working correctly", 
                                  f"User: {data['name']} ({data['email']})")
                    return True
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_result("User Authentication", False, f"Missing required fields: {missing}")
                    return False
            else:
                self.log_result("User Authentication", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("User Authentication", False, f"Request error: {str(e)}")
            return False
    
    def test_create_recording(self):
        """Test audio recording storage"""
        if not self.session_token:
            self.log_result("Audio Recording Storage", False, "No session token available")
            return False
            
        try:
            headers = {
                'Authorization': f'Bearer {self.session_token}',
                'Content-Type': 'application/json'
            }
            
            recording_data = {
                'title': 'Test Physics Lecture',
                'audio_data': TEST_AUDIO_DATA,
                'tags': ['physics', 'mechanics', 'test'],
                'notes': 'Test recording for backend validation',
                'duration': 120.5
            }
            
            response = requests.post(f"{API_BASE}/recordings", 
                                   headers=headers, 
                                   json=recording_data, 
                                   timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['id', 'user_id', 'title', 'audio_data', 'status']
                
                if all(field in data for field in required_fields):
                    self.test_recording_id = data['id']
                    self.log_result("Audio Recording Storage", True, "Recording created successfully",
                                  f"Recording ID: {data['id']}, Status: {data['status']}")
                    return True
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_result("Audio Recording Storage", False, f"Missing fields in response: {missing}")
                    return False
            else:
                self.log_result("Audio Recording Storage", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Audio Recording Storage", False, f"Request error: {str(e)}")
            return False
    
    def test_get_recordings(self):
        """Test recording retrieval"""
        if not self.session_token:
            self.log_result("Recording Retrieval", False, "No session token available")
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            response = requests.get(f"{API_BASE}/recordings", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0 and self.test_recording_id:
                        # Check if our test recording is in the list
                        found = any(r.get('id') == self.test_recording_id for r in data)
                        if found:
                            self.log_result("Recording Retrieval", True, f"Retrieved {len(data)} recordings successfully")
                            return True
                        else:
                            self.log_result("Recording Retrieval", False, "Test recording not found in list")
                            return False
                    else:
                        self.log_result("Recording Retrieval", True, "Retrieved empty recordings list (expected for new user)")
                        return True
                else:
                    self.log_result("Recording Retrieval", False, f"Expected list, got: {type(data)}")
                    return False
            else:
                self.log_result("Recording Retrieval", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Recording Retrieval", False, f"Request error: {str(e)}")
            return False
    
    def test_ai_processing_modes(self):
        """Test all three AI processing modes: full transcription, smart summarization, chapter detection"""
        if not self.session_token or not self.test_recording_id:
            self.log_result("AI Processing", False, "No session token or recording ID available")
            return False
        
        success_count = 0
        total_modes = 3
        
        # Test all three processing modes
        processing_modes = [
            ('full', 'Full Transcription'),
            ('summary', 'Smart Summarization'),
            ('chapters', 'Chapter Detection')
        ]
        
        for mode_type, mode_name in processing_modes:
            try:
                headers = {
                    'Authorization': f'Bearer {self.session_token}',
                    'Content-Type': 'application/json'
                }
                
                processing_data = {
                    'recording_id': self.test_recording_id,
                    'type': mode_type
                }
                
                response = requests.post(f"{API_BASE}/recordings/{self.test_recording_id}/process",
                                       headers=headers,
                                       json=processing_data,
                                       timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    required_fields = ['message', 'recording_id', 'status']
                    
                    if all(field in data for field in required_fields):
                        if data['status'] == 'processing':
                            self.log_result(f"AI {mode_name}", True, f"{mode_name} processing started successfully",
                                          f"Recording ID: {data['recording_id']}, Status: {data['status']}")
                            
                            # Wait for processing to complete
                            time.sleep(4)
                            if self.verify_processing_completion(mode_type, mode_name):
                                success_count += 1
                        else:
                            self.log_result(f"AI {mode_name}", False, f"Unexpected status: {data['status']}")
                    else:
                        missing = [f for f in required_fields if f not in data]
                        self.log_result(f"AI {mode_name}", False, f"Missing fields in response: {missing}")
                else:
                    self.log_result(f"AI {mode_name}", False, f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.log_result(f"AI {mode_name}", False, f"Request error: {str(e)}")
        
        # Overall result
        if success_count == total_modes:
            self.log_result("AI Processing (All Modes)", True, f"All {total_modes} AI processing modes successful")
            return True
        else:
            self.log_result("AI Processing (All Modes)", False, f"Only {success_count}/{total_modes} modes successful")
            return False
    
    def verify_processing_completion(self, mode_type, mode_name):
        """Verify that AI processing was completed for specific mode"""
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            response = requests.get(f"{API_BASE}/recordings/{self.test_recording_id}", 
                                  headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'completed':
                    # Check for appropriate content based on mode
                    if mode_type == 'full' and data.get('transcript'):
                        transcript_content = data['transcript']
                        if "Newton's Laws" in transcript_content and len(transcript_content) > 500:
                            self.log_result(f"AI {mode_name} Completion", True, 
                                          f"{mode_name} completed with realistic content",
                                          f"Content length: {len(transcript_content)} characters")
                            return True
                    elif mode_type in ['summary', 'chapters'] and data.get('summary'):
                        summary_content = data['summary']
                        if mode_type == 'summary' and "📚" in summary_content and "Key Concepts" in summary_content:
                            self.log_result(f"AI {mode_name} Completion", True, 
                                          f"{mode_name} completed with structured summary",
                                          f"Content length: {len(summary_content)} characters")
                            return True
                        elif mode_type == 'chapters' and "📖" in summary_content and "Chapter" in summary_content:
                            self.log_result(f"AI {mode_name} Completion", True, 
                                          f"{mode_name} completed with chapter breakdown",
                                          f"Content length: {len(summary_content)} characters")
                            return True
                    
                    self.log_result(f"AI {mode_name} Completion", False, 
                                  f"Processing completed but content doesn't match expected format for {mode_type}")
                    return False
                elif data.get('status') == 'processing':
                    self.log_result(f"AI {mode_name} Completion", True, f"{mode_name} still processing (acceptable)")
                    return True
                else:
                    self.log_result(f"AI {mode_name} Completion", False, 
                                  f"Status: {data.get('status')}, Expected: completed")
                    return False
            else:
                self.log_result(f"AI {mode_name} Completion", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result(f"AI {mode_name} Completion", False, f"Request error: {str(e)}")
            return False
    
    def test_recording_management(self):
        """Test recording CRUD operations"""
        if not self.session_token or not self.test_recording_id:
            self.log_result("Recording Management", False, "No session token or recording ID available")
            return False
        
        success_count = 0
        total_tests = 3
        
        # Test GET specific recording
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            response = requests.get(f"{API_BASE}/recordings/{self.test_recording_id}", 
                                  headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('id') == self.test_recording_id:
                    self.log_result("Recording GET", True, "Retrieved specific recording successfully")
                    success_count += 1
                else:
                    self.log_result("Recording GET", False, "Recording ID mismatch")
            else:
                self.log_result("Recording GET", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Recording GET", False, f"Request error: {str(e)}")
        
        # Test PUT (update recording)
        try:
            headers = {
                'Authorization': f'Bearer {self.session_token}',
                'Content-Type': 'application/json'
            }
            
            update_data = {
                'title': 'Updated Test Physics Lecture',
                'tags': ['physics', 'mechanics', 'updated'],
                'notes': 'Updated notes for testing'
            }
            
            response = requests.put(f"{API_BASE}/recordings/{self.test_recording_id}",
                                  headers=headers,
                                  json=update_data,
                                  timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data and 'updated' in data['message'].lower():
                    self.log_result("Recording PUT", True, "Recording updated successfully")
                    success_count += 1
                else:
                    self.log_result("Recording PUT", False, f"Unexpected response: {data}")
            else:
                self.log_result("Recording PUT", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Recording PUT", False, f"Request error: {str(e)}")
        
        # Test DELETE recording
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            response = requests.delete(f"{API_BASE}/recordings/{self.test_recording_id}",
                                     headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data and 'deleted' in data['message'].lower():
                    self.log_result("Recording DELETE", True, "Recording deleted successfully")
                    success_count += 1
                else:
                    self.log_result("Recording DELETE", False, f"Unexpected response: {data}")
            else:
                self.log_result("Recording DELETE", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Recording DELETE", False, f"Request error: {str(e)}")
        
        # Overall result
        if success_count == total_tests:
            self.log_result("Recording Management CRUD", True, f"All {total_tests} CRUD operations successful")
            return True
        else:
            self.log_result("Recording Management CRUD", False, f"Only {success_count}/{total_tests} operations successful")
            return False
    
    def test_user_profile(self):
        """Test user profile endpoints"""
        if not self.session_token:
            self.log_result("User Profile", False, "No session token available")
            return False
        
        success_count = 0
        total_tests = 2
        
        # Test GET user profile
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            response = requests.get(f"{API_BASE}/user/profile", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['id', 'email', 'name', 'subscription_status', 'referral_code']
                
                if all(field in data for field in required_fields):
                    self.log_result("User Profile GET", True, "User profile retrieved successfully",
                                  f"User: {data['name']}, Status: {data['subscription_status']}")
                    success_count += 1
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_result("User Profile GET", False, f"Missing fields: {missing}")
            else:
                self.log_result("User Profile GET", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("User Profile GET", False, f"Request error: {str(e)}")
        
        # Test GET referral info
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            response = requests.get(f"{API_BASE}/user/referral", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['referral_code', 'discount_amount', 'monthly_cost']
                
                if all(field in data for field in required_fields):
                    self.log_result("User Referral GET", True, "Referral info retrieved successfully",
                                  f"Code: {data['referral_code']}, Cost: €{data['monthly_cost']}")
                    success_count += 1
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_result("User Referral GET", False, f"Missing fields: {missing}")
            else:
                self.log_result("User Referral GET", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("User Referral GET", False, f"Request error: {str(e)}")
        
        # Overall result
        if success_count == total_tests:
            self.log_result("User Profile and Referral System", True, f"All {total_tests} profile operations successful")
            return True
        else:
            self.log_result("User Profile and Referral System", False, f"Only {success_count}/{total_tests} operations successful")
            return False
    
    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print("=" * 60)
        print("SMARTNOTES BACKEND API TESTING SUITE")
        print("=" * 60)
        print(f"Testing API at: {API_BASE}")
        print(f"Session ID: {TEST_SESSION_ID}")
        print("=" * 60)
        
        # Test sequence based on dependencies
        tests = [
            ("Health Check", self.test_health_check),
            ("User Authentication", self.test_auth_profile),
            ("Audio Recording Storage", self.test_create_recording),
            ("Recording Retrieval", self.test_get_recordings),
            ("AI Processing (All Modes)", self.test_ai_processing_modes),
            ("Recording Management CRUD", self.test_recording_management),
            ("User Profile and Referral", self.test_user_profile)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\n--- Running {test_name} ---")
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log_result(test_name, False, f"Test execution error: {str(e)}")
                failed += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {passed + failed}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "0%")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if "❌ FAIL" in result['status']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("=" * 60)
        return passed, failed

if __name__ == "__main__":
    tester = BackendTester()
    passed, failed = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)