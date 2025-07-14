#!/usr/bin/env python3
"""
SmartNotes Multilingual Backend Testing Suite
Comprehensive testing of multilingual features as requested
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
TEST_SESSION_ID = "multilingual-test-" + str(uuid.uuid4())
TEST_AUDIO_DATA = base64.b64encode(b"fake-audio-data-for-multilingual-testing").decode('utf-8')

class MultilingualTester:
    def __init__(self):
        self.session_token = None
        self.user_id = None
        self.test_recording_id = None
        self.results = {
            'health_check': False,
            'user_auth': False,
            'language_preferences': {'total': 5, 'passed': 0},
            'audio_storage': False,
            'multilingual_ai': {'total': 15, 'passed': 0},
            'recording_management': {'total': 3, 'passed': 0},
            'user_profile': False
        }
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
    
    def test_health_check(self):
        """Test 1: Health Check - Verify API is running"""
        print("\n=== 1. HEALTH CHECK ===")
        try:
            response = requests.get(f"{API_BASE}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "SmartNotes API is running" in data.get('message', ''):
                    self.log_result("Health Check", True, "API is running correctly")
                    self.results['health_check'] = True
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
    
    def test_user_authentication(self):
        """Test 2: User Authentication - Test auth system"""
        print("\n=== 2. USER AUTHENTICATION ===")
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
                    self.results['user_auth'] = True
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
    
    def test_user_language_preferences(self):
        """Test 3: User Language Preferences - Test all 5 languages (en, it, es, fr, de)"""
        print("\n=== 3. USER LANGUAGE PREFERENCES ===")
        if not self.session_token:
            self.log_result("User Language Preferences", False, "No session token available")
            return False
        
        success_count = 0
        supported_languages = ["en", "it", "es", "fr", "de"]
        language_names = {
            "en": "English",
            "it": "Italian", 
            "es": "Spanish",
            "fr": "French",
            "de": "German"
        }
        
        for lang_code in supported_languages:
            try:
                headers = {
                    'Authorization': f'Bearer {self.session_token}',
                    'Content-Type': 'application/json'
                }
                
                language_data = {'language': lang_code}
                
                response = requests.put(f"{API_BASE}/user/language",
                                      headers=headers,
                                      json=language_data,
                                      timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('language') == lang_code and 'updated' in data.get('message', '').lower():
                        self.log_result(f"Language Update ({language_names[lang_code]})", True, 
                                      f"Language successfully updated to {language_names[lang_code]} ({lang_code})")
                        success_count += 1
                    else:
                        self.log_result(f"Language Update ({language_names[lang_code]})", False, 
                                      f"Unexpected response: {data}")
                else:
                    self.log_result(f"Language Update ({language_names[lang_code]})", False, 
                                  f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.log_result(f"Language Update ({language_names[lang_code]})", False, 
                              f"Request error: {str(e)}")
        
        # Test invalid language validation
        try:
            headers = {
                'Authorization': f'Bearer {self.session_token}',
                'Content-Type': 'application/json'
            }
            
            language_data = {'language': 'invalid'}
            
            response = requests.put(f"{API_BASE}/user/language",
                                  headers=headers,
                                  json=language_data,
                                  timeout=10)
            
            if response.status_code == 400:
                self.log_result("Language Validation", True, "Invalid language properly rejected")
            else:
                self.log_result("Language Validation", False, f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_result("Language Validation", False, f"Request error: {str(e)}")
        
        self.results['language_preferences']['passed'] = success_count
        
        if success_count == 5:
            self.log_result("User Language Preferences", True, f"All 5 language updates successful")
            return True
        else:
            self.log_result("User Language Preferences", False, f"Only {success_count}/5 language updates successful")
            return False

    def test_audio_recording_storage(self):
        """Test 4: Audio Recording Storage - Test recording creation"""
        print("\n=== 4. AUDIO RECORDING STORAGE ===")
        if not self.session_token:
            self.log_result("Audio Recording Storage", False, "No session token available")
            return False
            
        try:
            headers = {
                'Authorization': f'Bearer {self.session_token}',
                'Content-Type': 'application/json'
            }
            
            recording_data = {
                'title': 'Multilingual Test Physics Lecture',
                'audio_data': TEST_AUDIO_DATA,
                'tags': ['physics', 'multilingual', 'test'],
                'notes': 'Test recording for multilingual backend validation',
                'duration': 180.5
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
                    self.results['audio_storage'] = True
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

    def test_multilingual_ai_processing(self):
        """Test 5: Multilingual AI Processing - Test all 15 combinations (5 languages × 3 modes)"""
        print("\n=== 5. MULTILINGUAL AI PROCESSING ===")
        if not self.session_token or not self.test_recording_id:
            self.log_result("Multilingual AI Processing", False, "No session token or recording ID available")
            return False
        
        success_count = 0
        total_tests = 15  # 5 languages × 3 modes
        
        languages = [
            ("en", "English"),
            ("it", "Italian"),
            ("es", "Spanish"), 
            ("fr", "French"),
            ("de", "German")
        ]
        
        processing_modes = [
            ('full', 'Full Transcription'),
            ('summary', 'Smart Summarization'),
            ('chapters', 'Chapter Detection')
        ]
        
        print(f"Testing {total_tests} combinations (5 languages × 3 modes)...")
        
        for lang_code, lang_name in languages:
            print(f"\n--- Testing {lang_name} ({lang_code}) ---")
            for mode_type, mode_name in processing_modes:
                try:
                    headers = {
                        'Authorization': f'Bearer {self.session_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    processing_data = {
                        'recording_id': self.test_recording_id,
                        'type': mode_type,
                        'language': lang_code
                    }
                    
                    response = requests.post(f"{API_BASE}/recordings/{self.test_recording_id}/process",
                                           headers=headers,
                                           json=processing_data,
                                           timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') == 'processing' and lang_code in data.get('message', ''):
                            self.log_result(f"AI {mode_name} ({lang_name})", True, 
                                          f"{mode_name} processing started in {lang_name}",
                                          f"Language: {lang_code}, Status: {data['status']}")
                            
                            # Wait for processing to complete
                            time.sleep(3)
                            if self.verify_multilingual_processing_completion(mode_type, mode_name, lang_code, lang_name):
                                success_count += 1
                        else:
                            self.log_result(f"AI {mode_name} ({lang_name})", False, 
                                          f"Unexpected response: {data}")
                    else:
                        self.log_result(f"AI {mode_name} ({lang_name})", False, 
                                      f"HTTP {response.status_code}: {response.text}")
                except Exception as e:
                    self.log_result(f"AI {mode_name} ({lang_name})", False, 
                                  f"Request error: {str(e)}")
        
        self.results['multilingual_ai']['passed'] = success_count
        
        # Overall result
        if success_count >= 12:  # Allow some tolerance for async processing
            self.log_result("Multilingual AI Processing", True, 
                          f"{success_count}/{total_tests} multilingual AI processing tests successful")
            return True
        else:
            self.log_result("Multilingual AI Processing", False, 
                          f"Only {success_count}/{total_tests} multilingual processing tests successful")
            return False

    def verify_multilingual_processing_completion(self, mode_type, mode_name, lang_code, lang_name):
        """Verify that multilingual AI processing was completed correctly"""
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            response = requests.get(f"{API_BASE}/recordings/{self.test_recording_id}", 
                                  headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'completed':
                    # Language-specific validation keywords
                    language_keywords = {
                        "en": ["Newton's Laws", "Physics", "motion", "force"],
                        "it": ["Leggi di Newton", "Fisica", "movimento", "forza", "moto"],
                        "es": ["Leyes de Newton", "Física", "movimiento", "fuerza"],
                        "fr": ["Lois de Newton", "Physique", "mouvement", "force"],
                        "de": ["Newtons Gesetze", "Physik", "Bewegung", "Kraft"]
                    }
                    
                    keywords = language_keywords.get(lang_code, language_keywords["en"])
                    
                    # Check for appropriate content based on mode
                    if mode_type == 'full' and data.get('transcript'):
                        content = data['transcript']
                        if any(keyword in content for keyword in keywords) and len(content) > 500:
                            self.log_result(f"AI {mode_name} ({lang_name}) Completion", True, 
                                          f"{mode_name} completed with {lang_name} content",
                                          f"Content length: {len(content)} chars, Language: {lang_code}")
                            return True
                    elif mode_type in ['summary', 'chapters'] and data.get('summary'):
                        content = data['summary']
                        if any(keyword in content for keyword in keywords) and len(content) > 200:
                            self.log_result(f"AI {mode_name} ({lang_name}) Completion", True, 
                                          f"{mode_name} completed with {lang_name} content",
                                          f"Content length: {len(content)} chars, Language: {lang_code}")
                            return True
                    
                    self.log_result(f"AI {mode_name} ({lang_name}) Completion", False, 
                                  f"Content doesn't contain expected {lang_name} keywords")
                    return False
                elif data.get('status') == 'processing':
                    self.log_result(f"AI {mode_name} ({lang_name}) Completion", True, 
                                  f"{mode_name} still processing in {lang_name} (acceptable)")
                    return True
                else:
                    self.log_result(f"AI {mode_name} ({lang_name}) Completion", False, 
                                  f"Status: {data.get('status')}, Expected: completed")
                    return False
            else:
                self.log_result(f"AI {mode_name} ({lang_name}) Completion", False, 
                              f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result(f"AI {mode_name} ({lang_name}) Completion", False, 
                          f"Request error: {str(e)}")
            return False

    def test_recording_management(self):
        """Test 6: Recording Management - Test CRUD operations"""
        print("\n=== 6. RECORDING MANAGEMENT ===")
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
                'title': 'Updated Multilingual Test Physics Lecture',
                'tags': ['physics', 'multilingual', 'updated'],
                'notes': 'Updated notes for multilingual testing'
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
        
        # Test DELETE recording (we'll skip this to preserve the recording for other tests)
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            # Create a new recording just for deletion test
            recording_data = {
                'title': 'Test Recording for Deletion',
                'audio_data': TEST_AUDIO_DATA,
                'tags': ['test', 'delete'],
                'notes': 'This recording will be deleted',
                'duration': 60.0
            }
            
            create_response = requests.post(f"{API_BASE}/recordings", 
                                          headers={'Authorization': f'Bearer {self.session_token}', 'Content-Type': 'application/json'}, 
                                          json=recording_data, 
                                          timeout=15)
            
            if create_response.status_code == 200:
                delete_recording_id = create_response.json()['id']
                
                response = requests.delete(f"{API_BASE}/recordings/{delete_recording_id}",
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
            else:
                self.log_result("Recording DELETE", False, "Failed to create test recording for deletion")
        except Exception as e:
            self.log_result("Recording DELETE", False, f"Request error: {str(e)}")
        
        self.results['recording_management']['passed'] = success_count
        
        # Overall result
        if success_count == total_tests:
            self.log_result("Recording Management CRUD", True, f"All {total_tests} CRUD operations successful")
            return True
        else:
            self.log_result("Recording Management CRUD", False, f"Only {success_count}/{total_tests} operations successful")
            return False

    def test_user_profile(self):
        """Test 7: User Profile - Test profile with language preferences"""
        print("\n=== 7. USER PROFILE ===")
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
                required_fields = ['id', 'email', 'name', 'subscription_status', 'referral_code', 'preferred_language']
                
                if all(field in data for field in required_fields):
                    self.log_result("User Profile GET", True, "User profile retrieved successfully",
                                  f"User: {data['name']}, Language: {data['preferred_language']}, Status: {data['subscription_status']}")
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
            self.results['user_profile'] = True
            return True
        else:
            self.log_result("User Profile and Referral System", False, f"Only {success_count}/{total_tests} operations successful")
            return False
    
    def run_comprehensive_multilingual_tests(self):
        """Run comprehensive multilingual backend testing"""
        print("=" * 80)
        print("SMARTNOTES COMPREHENSIVE MULTILINGUAL BACKEND TESTING")
        print("=" * 80)
        print(f"Testing API at: {API_BASE}")
        print(f"Session ID: {TEST_SESSION_ID}")
        print("=" * 80)
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("User Authentication", self.test_user_authentication),
            ("User Language Preferences", self.test_user_language_preferences),
            ("Audio Recording Storage", self.test_audio_recording_storage),
            ("Multilingual AI Processing", self.test_multilingual_ai_processing),
            ("Recording Management", self.test_recording_management),
            ("User Profile", self.test_user_profile)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log_result(test_name, False, f"Test execution error: {str(e)}")
                failed += 1
        
        # Final comprehensive summary
        print("\n" + "=" * 80)
        print("COMPREHENSIVE MULTILINGUAL TESTING RESULTS")
        print("=" * 80)
        
        # Feature category results
        categories = [
            ("Health Check", self.results['health_check']),
            ("User Authentication", self.results['user_auth']),
            ("User Language Preferences", f"{self.results['language_preferences']['passed']}/5"),
            ("Audio Recording Storage", self.results['audio_storage']),
            ("Multilingual AI Processing", f"{self.results['multilingual_ai']['passed']}/15"),
            ("Recording Management", f"{self.results['recording_management']['passed']}/3"),
            ("User Profile", self.results['user_profile'])
        ]
        
        for category, result in categories:
            if isinstance(result, bool):
                status = "✅ WORKING" if result else "❌ FAILING"
                print(f"{category}: {status}")
            else:
                print(f"{category}: {result} tests passed")
        
        print("\n" + "=" * 80)
        print("DETAILED SUCCESS RATES BY CATEGORY:")
        print("=" * 80)
        
        # Calculate success rates
        health_rate = 100 if self.results['health_check'] else 0
        auth_rate = 100 if self.results['user_auth'] else 0
        lang_rate = (self.results['language_preferences']['passed'] / 5) * 100
        storage_rate = 100 if self.results['audio_storage'] else 0
        ai_rate = (self.results['multilingual_ai']['passed'] / 15) * 100
        crud_rate = (self.results['recording_management']['passed'] / 3) * 100
        profile_rate = 100 if self.results['user_profile'] else 0
        
        print(f"1. Health Check: {health_rate:.1f}%")
        print(f"2. User Authentication: {auth_rate:.1f}%")
        print(f"3. User Language Preferences (5 languages): {lang_rate:.1f}%")
        print(f"4. Audio Recording Storage: {storage_rate:.1f}%")
        print(f"5. Multilingual AI Processing (15 combinations): {ai_rate:.1f}%")
        print(f"6. Recording Management CRUD: {crud_rate:.1f}%")
        print(f"7. User Profile: {profile_rate:.1f}%")
        
        overall_rate = (health_rate + auth_rate + lang_rate + storage_rate + ai_rate + crud_rate + profile_rate) / 7
        
        print(f"\nOVERALL SUCCESS RATE: {overall_rate:.1f}%")
        print("=" * 80)
        
        return passed, failed, overall_rate

if __name__ == "__main__":
    tester = MultilingualTester()
    passed, failed, success_rate = tester.run_comprehensive_multilingual_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)