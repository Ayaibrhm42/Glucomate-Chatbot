"""
GlucoMate Level 5: Personalized Care
Inherits: Bedrock core, safety, multilingual, knowledge base, smart search
Adds: Patient profiles, medication tracking, personalized responses
"""

import boto3
import json
import sys
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from smart_search_glucomate import SmartMedicalSearchGlucoMate

class PatientDatabase:
    """Database handler for patient information"""
    
    def __init__(self, db_path="patient_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize patient database with all necessary tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Patient profile table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_profile (
                patient_id TEXT PRIMARY KEY,
                name TEXT,
                age INTEGER,
                diabetes_type TEXT,
                diagnosis_date TEXT,
                hba1c REAL,
                target_glucose_min INTEGER,
                target_glucose_max INTEGER,
                weight REAL,
                height REAL,
                activity_level TEXT,
                dietary_restrictions TEXT,
                allergies TEXT,
                language_preference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Medications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                medication_name TEXT,
                dosage TEXT,
                frequency TEXT,
                time_slots TEXT,
                start_date TEXT,
                end_date TEXT,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        # Glucose readings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS glucose_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                reading REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                meal_context TEXT,
                notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        # Meal preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meal_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                preferred_foods TEXT,
                disliked_foods TEXT,
                cultural_preferences TEXT,
                budget_range TEXT,
                cooking_skills TEXT,
                meal_prep_time TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_patient_profile(self, patient_id):
        """Get complete patient profile with all related data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get main profile
            cursor.execute('SELECT * FROM patient_profile WHERE patient_id = ?', (patient_id,))
            profile = cursor.fetchone()
            
            if not profile:
                return None
            
            # Convert to dictionary
            columns = [desc[0] for desc in cursor.description]
            profile_dict = dict(zip(columns, profile))
            
            # Get medications
            cursor.execute('SELECT * FROM medications WHERE patient_id = ? AND active = 1', (patient_id,))
            medications = cursor.fetchall()
            profile_dict['medications'] = medications
            
            # Get meal preferences
            cursor.execute('SELECT * FROM meal_preferences WHERE patient_id = ?', (patient_id,))
            meal_prefs = cursor.fetchone()
            profile_dict['meal_preferences'] = meal_prefs
            
            # Get recent glucose readings
            cursor.execute('''
                SELECT * FROM glucose_readings WHERE patient_id = ? 
                ORDER BY timestamp DESC LIMIT 10
            ''', (patient_id,))
            recent_readings = cursor.fetchall()
            profile_dict['recent_readings'] = recent_readings
            
            return profile_dict
            
        except Exception as e:
            print(f"Error getting patient profile: {e}")
            return None
        finally:
            conn.close()
    
    def save_patient_profile(self, patient_data):
        """Save or update patient profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert or update patient profile
            cursor.execute('''
                INSERT OR REPLACE INTO patient_profile 
                (patient_id, name, age, diabetes_type, hba1c, target_glucose_min, target_glucose_max, 
                 weight, height, activity_level, dietary_restrictions, allergies, language_preference, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_data.get('patient_id'),
                patient_data.get('name'),
                patient_data.get('age'),
                patient_data.get('diabetes_type'),
                patient_data.get('hba1c'),
                patient_data.get('target_glucose_min', 80),
                patient_data.get('target_glucose_max', 130),
                patient_data.get('weight'),
                patient_data.get('height'),
                patient_data.get('activity_level'),
                patient_data.get('dietary_restrictions'),
                patient_data.get('allergies'),
                patient_data.get('language_preference', 'en'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving patient profile: {e}")
            return False
        finally:
            conn.close()

class PersonalizedGlucoMate(SmartMedicalSearchGlucoMate):
    """
    Level 5: Adds personalization and patient data management
    Inherits: Bedrock core, safety, multilingual, knowledge base, smart search
    Adds: Patient profiles, medication tracking, personalized responses
    """
    
    def __init__(self, patient_id=None):
        super().__init__()  # Get ALL previous functionality
        
        # Patient-specific data
        self.patient_id = patient_id
        self.patient_profile = None
        self.medication_timer = None
        self.conversation_active = False
        
        # Database setup
        self.patient_db = PatientDatabase()
        
        # Profile collection state
        self.collecting_profile = False
        self.profile_questions = [
            {
                "field": "name",
                "question": "What's your name? (This helps me personalize our conversations)",
                "required": False
            },
            {
                "field": "diabetes_type",
                "question": "What type of diabetes do you have? (Type 1, Type 2, or Gestational)",
                "required": True
            },
            {
                "field": "age", 
                "question": "What's your age? (This helps me give age-appropriate advice)",
                "required": True
            },
            {
                "field": "activity_level",
                "question": "How would you describe your activity level? (Sedentary, Light, Moderate, Active, Very Active)",
                "required": True
            },
            {
                "field": "dietary_restrictions",
                "question": "Do you have any dietary restrictions? (Vegetarian, Vegan, Halal, Kosher, None, etc.)",
                "required": False
            },
            {
                "field": "target_glucose_min",
                "question": "What's your target blood sugar range? Please give me the LOW number (usually 80-100)",
                "required": False
            },
            {
                "field": "target_glucose_max", 
                "question": "And what's the HIGH number of your target range? (usually 120-180)",
                "required": False
            }
        ]
        self.current_question_index = 0
        self.temp_profile_data = {}
        self.original_request = None
        
        if patient_id:
            self.load_patient_data()
            self.start_medication_monitoring()
        
        print("👤 GlucoMate Level 5: Personalization engine loaded")
    
    def load_patient_data(self):
        """Load patient data from database"""
        if self.patient_id:
            self.patient_profile = self.patient_db.get_patient_profile(self.patient_id)
            if self.patient_profile:
                name = self.patient_profile.get('name', 'there')
                diabetes_type = self.patient_profile.get('diabetes_type', 'diabetes')
                print(f"👋 Welcome back, {name}! Ready to help with your {diabetes_type} management.")
            else:
                print(f"📝 New patient profile will be created for ID: {self.patient_id}")
    
    def start_medication_monitoring(self):
        """Start background medication reminder monitoring"""
        if self.patient_profile and self.patient_profile.get('medications'):
            self.medication_timer = threading.Thread(target=self._medication_monitor, daemon=True)
            self.medication_timer.start()
            print("💊 Medication reminder system activated")
    
    def _medication_monitor(self):
        """Background medication reminder checker"""
        while self.conversation_active:
            try:
                reminder = self.check_medication_time()
                if reminder:
                    print(f"\n🔔 MEDICATION REMINDER: {reminder}")
                    # In a real implementation, this would interrupt the conversation appropriately
                
                time.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Medication monitoring error: {e}")
                break
    
    def check_medication_time(self):
        """Check if it's time for any medication"""
        if not self.patient_profile or not self.patient_profile.get('medications'):
            return None
        
        current_time = datetime.now().time()
        current_hour_minute = current_time.strftime("%H:%M")
        
        for medication in self.patient_profile['medications']:
            med_name = medication[2]  # medication_name
            time_slots = medication[5]  # time_slots (JSON string)
            
            if time_slots:
                try:
                    times = json.loads(time_slots)
                    for time_slot in times:
                        # Check if within 5 minutes of medication time
                        if abs(self._time_difference_minutes(current_hour_minute, time_slot)) <= 2:
                            return f"Time for your {med_name}! 💊"
                except Exception as e:
                    print(f"Error parsing medication times: {e}")
        
        return None
    
    def _time_difference_minutes(self, time1, time2):
        """Calculate difference between two time strings in minutes"""
        try:
            t1 = datetime.strptime(time1, "%H:%M").time()
            t2 = datetime.strptime(time2, "%H:%M").time()
            
            # Convert to minutes since midnight
            t1_minutes = t1.hour * 60 + t1.minute
            t2_minutes = t2.hour * 60 + t2.minute
            
            return abs(t1_minutes - t2_minutes)
        except:
            return 999  # Large number if parsing fails
    
    def check_profile_completeness(self):
        """Check if patient has sufficient data for personalization"""
        if not self.patient_profile:
            return {"complete": False, "missing": "all", "has_some_data": False}
        
        # Essential fields for personalization
        essential_fields = ['diabetes_type', 'age']
        helpful_fields = ['activity_level', 'dietary_restrictions', 'target_glucose_min']
        
        missing_essential = [field for field in essential_fields 
                           if not self.patient_profile.get(field)]
        missing_helpful = [field for field in helpful_fields 
                         if not self.patient_profile.get(field)]
        
        return {
            "complete": len(missing_essential) == 0,
            "missing_essential": missing_essential,
            "missing_helpful": missing_helpful,
            "has_some_data": len(missing_essential) < len(essential_fields)
        }
    
    def start_profile_collection(self, original_request=""):
        """Start collecting profile data through conversation"""
        self.collecting_profile = True
        self.current_question_index = 0
        self.temp_profile_data = {'patient_id': self.patient_id}
        self.original_request = original_request
        
        welcome_msg = f"""
        Great! I'd love to personalize your diabetes care. I'll ask you a few questions to understand your specific needs better. 
        
        This information will be securely saved to help me give you more relevant advice in the future. You can say 'skip' for any question or 'stop' to exit.
        
        Let's get started! 🚀
        """
        
        first_question = self.get_current_profile_question()
        return welcome_msg + "\n\n" + first_question
    
    def get_current_profile_question(self):
        """Get the current question in profile collection"""
        if self.current_question_index >= len(self.profile_questions):
            return None
        
        question_data = self.profile_questions[self.current_question_index]
        required_text = " (Required)" if question_data["required"] else " (Optional)"
        
        return f"**Question {self.current_question_index + 1}/{len(self.profile_questions)}**{required_text}: {question_data['question']}"
    
    def process_profile_answer(self, user_input):
        """Process profile collection answers"""
        user_input_lower = user_input.lower().strip()
        
        # Handle stop commands
        if user_input_lower in ['stop', 'quit', 'cancel', 'exit']:
            self.collecting_profile = False
            return "No problem! You can always set up your profile later by saying 'create my profile'. What would you like to know about diabetes?"
        
        # Get current question
        if self.current_question_index >= len(self.profile_questions):
            return self.complete_profile_collection()
        
        current_question = self.profile_questions[self.current_question_index]
        field_name = current_question["field"]
        
        # Handle skip
        if user_input_lower == 'skip' and not current_question["required"]:
            self.temp_profile_data[field_name] = None
        elif user_input_lower == 'skip' and current_question["required"]:
            return f"This question helps me give you better care. {current_question['question']}"
        else:
            # Validate and store answer
            validated = self.validate_profile_answer(field_name, user_input)
            if validated["valid"]:
                self.temp_profile_data[field_name] = validated["value"]
            else:
                return f"I didn't understand that. {validated['error']} Please try again: {current_question['question']}"
        
        # Move to next question
        self.current_question_index += 1
        
        if self.current_question_index < len(self.profile_questions):
            next_question = self.get_current_profile_question()
            progress = f"Thanks! ({self.current_question_index}/{len(self.profile_questions)} completed)\n\n"
            return progress + next_question
        else:
            return self.complete_profile_collection()
    
    def validate_profile_answer(self, field_name, user_input):
        """Validate profile answers"""
        user_input = user_input.strip()
        
        if field_name == "diabetes_type":
            type_mapping = {
                "type 1": "Type 1", "type1": "Type 1", "t1": "Type 1", "1": "Type 1",
                "type 2": "Type 2", "type2": "Type 2", "t2": "Type 2", "2": "Type 2",
                "gestational": "Gestational", "gdm": "Gestational"
            }
            normalized = user_input.lower()
            if normalized in type_mapping:
                return {"valid": True, "value": type_mapping[normalized]}
            return {"valid": False, "error": "Please specify Type 1, Type 2, or Gestational diabetes."}
        
        elif field_name == "age":
            try:
                age = int(user_input)
                if 1 <= age <= 120:
                    return {"valid": True, "value": age}
                return {"valid": False, "error": "Please enter an age between 1 and 120."}
            except:
                return {"valid": False, "error": "Please enter your age as a number."}
        
        elif field_name in ["target_glucose_min", "target_glucose_max"]:
            try:
                glucose = int(user_input)
                if 50 <= glucose <= 300:
                    return {"valid": True, "value": glucose}
                return {"valid": False, "error": "Please enter a glucose value between 50-300 mg/dL."}
            except:
                return {"valid": False, "error": "Please enter a number for glucose levels."}
        
        elif field_name == "activity_level":
            activity_mapping = {
                "sedentary": "Sedentary", "inactive": "Sedentary",
                "light": "Light", "lightly active": "Light",
                "moderate": "Moderate", "moderately active": "Moderate",
                "active": "Active", "very active": "Very Active", "highly active": "Very Active"
            }
            normalized = user_input.lower()
            for key, value in activity_mapping.items():
                if key in normalized:
                    return {"valid": True, "value": value}
            return {"valid": False, "error": "Please choose: Sedentary, Light, Moderate, Active, or Very Active."}
        
        else:
            # For text fields, just clean and return
            return {"valid": True, "value": user_input.strip() if user_input.strip() else None}
    
    def complete_profile_collection(self):
        """Complete profile collection and save data"""
        self.collecting_profile = False
        
        # Save to database
        success = self.patient_db.save_patient_profile(self.temp_profile_data)
        
        if success:
            # Reload patient profile
            self.load_patient_data()
            
            completion_msg = """
            🎉 Perfect! Your profile has been saved. Now I can give you much more personalized diabetes care!
            
            Your profile includes:
            """
            
            for key, value in self.temp_profile_data.items():
                if value and key != 'patient_id':
                    readable_key = key.replace('_', ' ').title()
                    completion_msg += f"✅ {readable_key}: {value}\n"
            
            completion_msg += "\nNow I can provide personalized meal plans, medication reminders, and targeted advice! 🌟"
            
            # Clear temp data
            self.temp_profile_data = {}
            
            return completion_msg
        else:
            return "❌ Sorry, there was an issue saving your profile. Please try again later."
    
    def create_personalized_prompt(self, user_input, language="English", conversation_type="medical"):
        """Create prompts that include patient context"""
        
        # Build patient context
        patient_context = ""
        if self.patient_profile:
            name = self.patient_profile.get('name', 'Patient')
            diabetes_type = self.patient_profile.get('diabetes_type', 'diabetes')
            age = self.patient_profile.get('age')
            target_min = self.patient_profile.get('target_glucose_min', 80)
            target_max = self.patient_profile.get('target_glucose_max', 130)
            activity = self.patient_profile.get('activity_level')
            restrictions = self.patient_profile.get('dietary_restrictions')
            
            patient_context = f"""
            Patient Context for {name}:
            - Diabetes Type: {diabetes_type}
            - Age: {age if age else 'Not specified'}
            - Target Glucose Range: {target_min}-{target_max} mg/dL
            - Activity Level: {activity if activity else 'Not specified'}
            - Dietary Restrictions: {restrictions if restrictions else 'None specified'}
            - Recent Average Glucose: {self._get_recent_glucose_summary()}
            
            Personalization Instructions:
            - Address them by name when appropriate
            - Reference their specific diabetes type in advice
            - Consider their target range when discussing blood sugar
            - Adapt exercise advice to their activity level
            - Respect their dietary restrictions in food recommendations
            """
        
        # Use inherited base prompt and enhance with personalization
        if conversation_type == "casual":
            base_prompt = self.create_base_diabetes_prompt(
                user_input, 
                additional_context=patient_context,
                language=language, 
                conversation_type=conversation_type
            )
        else:
            # For medical conversations, add personalization context
            enhanced_context = patient_context + """
            
            Make your response highly personalized by:
            1. Using their name naturally in conversation
            2. Referencing their specific diabetes type and management needs
            3. Considering their personal target ranges and goals
            4. Providing advice appropriate for their age and activity level
            5. Respecting their dietary preferences and restrictions
            6. Connecting advice to their personal diabetes journey
            """
            
            base_prompt = self.create_base_diabetes_prompt(
                user_input,
                additional_context=enhanced_context,
                language=language,
                conversation_type=conversation_type
            )
        
        return base_prompt
    
    def _get_recent_glucose_summary(self):
        """Get summary of recent glucose readings"""
        if not self.patient_profile or not self.patient_profile.get('recent_readings'):
            return "No recent readings available"
        
        readings = self.patient_profile['recent_readings']
        if readings:
            avg_reading = sum(reading[2] for reading in readings) / len(readings)
            return f"Average of last {len(readings)} readings: {avg_reading:.1f} mg/dL"
        return "No recent readings"
    
    def generate_personalized_meal_plan(self, target_language_code='en'):
        """Generate meal plan based on patient profile"""
        if not self.patient_profile:
            return "I'd love to create a personalized meal plan! Let me first get to know you better. Would you like to set up your profile?"
        
        profile = self.patient_profile
        name = profile.get('name', 'friend')
        
        meal_plan_prompt = f"""
        Create a highly personalized 3-day diabetes meal plan for {name}:
        
        Patient Profile:
        - Name: {profile.get('name', 'Patient')}
        - Diabetes Type: {profile.get('diabetes_type', 'Not specified')}
        - Age: {profile.get('age', 'Not specified')}
        - Target Glucose Range: {profile.get('target_glucose_min', 80)}-{profile.get('target_glucose_max', 130)} mg/dL
        - Activity Level: {profile.get('activity_level', 'Moderate')}
        - Dietary Restrictions: {profile.get('dietary_restrictions', 'None')}
        - Recent Glucose Average: {self._get_recent_glucose_summary()}
        
        Create a meal plan that:
        1. Is specifically tailored to their diabetes type
        2. Fits their target glucose range
        3. Matches their activity level (calories and timing)
        4. Respects their dietary restrictions completely
        5. Is age-appropriate
        6. Includes practical tips for {name} specifically
        7. Has encouraging, personal language throughout
        
        Format: 3 days with breakfast, lunch, dinner, and 2 snacks each day.
        Include carb counts, portion sizes, and personalized tips for {name}.
        """
        
        response = self.call_bedrock_model(meal_plan_prompt, conversation_type="medical")
        
        if target_language_code != 'en':
            response = self.enhance_medical_translation(response, target_language_code)
        
        return response
    
    def personalized_chat(self, user_input, target_language_code='en', auto_detect=False):
        """
        Main personalized chat function with all inherited features
        
        This integrates ALL previous levels:
        - Bedrock core and safety (Level 1)
        - Multilingual support (Level 2) 
        - Knowledge base (Level 3)
        - Smart search (Level 4)
        - Personalization (Level 5)
        """
        self.conversation_active = True
        
        # Handle profile collection if in progress
        if self.collecting_profile:
            return self.process_profile_answer(user_input)
        
        # Check for medication reminders
        if self.patient_profile:
            med_reminder = self.check_medication_time()
            if med_reminder:
                return f"🔔 Hi {self.patient_profile.get('name', 'there')}! {med_reminder} Now, what were you asking about?"
        
        # Handle profile setup requests
        profile_triggers = [
            'create my profile', 'set up profile', 'personalize', 'my information',
            'tell you about me', 'get to know me'
        ]
        if any(trigger in user_input.lower() for trigger in profile_triggers):
            return self.start_profile_collection(user_input)
        
        # Handle personalized meal plan requests
        if 'meal plan' in user_input.lower() or 'diet plan' in user_input.lower():
            profile_status = self.check_profile_completeness()
            
            if profile_status["complete"]:
                print("👨‍🍳 Creating personalized meal plan...")
                return self.generate_personalized_meal_plan(target_language_code)
            elif profile_status["has_some_data"]:
                return self.generate_semi_personalized_response(user_input, target_language_code)
            else:
                return "I'd love to create a personalized meal plan for you! First, let me get to know you better. Would you like to set up your profile? Just say 'yes' and I'll ask you a few quick questions."
        
        # Use smart search functionality with personalization (inherits ALL previous features)
        response = self.smart_search_chat(user_input, target_language_code, auto_detect)
        
        # Enhance response with personalization if profile exists
        if self.patient_profile and not any(word in response for word in ['emergency', 'call 911', 'hospital']):
            # Add personal touches to non-emergency responses
            name = self.patient_profile.get('name')
            if name and len(response) > 100:  # Only for substantial responses
                personal_prompt = f"""
                Take this response and make it more personal for {name} who has {self.patient_profile.get('diabetes_type', 'diabetes')}:
                
                {response}
                
                Add personal touches like:
                - Use their name naturally (don't overuse it)
                - Reference their diabetes type when relevant
                - Make it feel like advice from a friend who knows them
                
                Keep all the medical accuracy and disclaimers. Just make it more personal and warm.
                """
                
                try:
                    personalized_response = self.call_bedrock_model(
                        personal_prompt, 
                        conversation_type="medical",
                        temperature=0.4
                    )
                    return personalized_response
                except:
                    # Fallback to original response if personalization fails
                    pass
        
        return response
    
    def generate_semi_personalized_response(self, user_input, target_language_code):
        """Generate response with partial profile data"""
        profile = self.patient_profile
        available_info = {k: v for k, v in profile.items() if v is not None}
        
        response_prompt = f"""
        Create a diabetes response using this partial patient information:
        
        Available Patient Data:
        {json.dumps(available_info, indent=2)}
        
        User Request: {user_input}
        
        Provide helpful advice that incorporates what we know about the patient while being clear about what additional information would help give even better guidance.
        """
        
        response = self.call_bedrock_model(response_prompt, conversation_type="medical")
        
        # Add offer to complete profile
        completion_offer = f"\n\n💡 **Want even better personalized advice?** I notice I'm missing some details about your preferences and goals. Would you like to complete your profile? Just say 'complete my profile'!"
        
        if target_language_code != 'en':
            response = self.enhance_medical_translation(response, target_language_code)
            completion_offer = self.translate_response(completion_offer, target_language_code)
        
        return response + completion_offer

def setup_demo_patient():
    """Set up demo patient for testing"""
    db = PatientDatabase()
    
    demo_data = {
        'patient_id': 'demo_patient_personalized',
        'name': 'Sarah Johnson', 
        'age': 34,
        'diabetes_type': 'Type 2',
        'hba1c': 7.2,
        'target_glucose_min': 80,
        'target_glucose_max': 130,
        'weight': 68.5,
        'activity_level': 'Moderate',
        'dietary_restrictions': 'Vegetarian',
        'language_preference': 'en'
    }
    
    success = db.save_patient_profile(demo_data)
    if success:
        print("✅ Demo patient profile created successfully!")
    return 'demo_patient_personalized'

def main():
    """Demo of Level 5 - Personalized GlucoMate"""
    print("👤 GlucoMate Level 5: Personalized Diabetes Care")
    print("🎯 Now with patient profiles, medication reminders, and tailored advice!")
    print("\n✨ New Features:")
    print("   • Personal patient profiles and data storage")
    print("   • Medication reminder system")
    print("   • Personalized meal plans and advice")
    print("   • Tailored responses based on diabetes type, age, and preferences")
    print("   • All previous features (multilingual, knowledge base, smart search)")
    
    # Set up demo patient
    demo_patient_id = setup_demo_patient()
    
    bot = PersonalizedGlucoMate(patient_id=demo_patient_id)
    
    # Show personalization info
    if bot.patient_profile:
        profile = bot.patient_profile
        print(f"\n👤 Patient Profile Loaded:")
        print(f"   • Name: {profile.get('name', 'Not set')}")
        print(f"   • Diabetes Type: {profile.get('diabetes_type', 'Not set')}")
        print(f"   • Age: {profile.get('age', 'Not set')}")
        print(f"   • Target Range: {profile.get('target_glucose_min', 80)}-{profile.get('target_glucose_max', 130)} mg/dL")
        print(f"   • Activity Level: {profile.get('activity_level', 'Not set')}")
    
    # Language selection (inherited)
    language_name, language_code = bot.get_language_choice()
    
    # Personalized greeting
    if bot.patient_profile:
        name = bot.patient_profile.get('name', 'there')
        diabetes_type = bot.patient_profile.get('diabetes_type', 'diabetes')
        greeting = f"Hello {name}! I'm here to help you manage your {diabetes_type} with personalized care."
    else:
        greeting = bot.get_cultural_greeting(language_code)
    
    if language_code != 'en':
        greeting = bot.translate_response(greeting, language_code)
    
    print(f"\n💙 {greeting}")
    
    # Personalized suggestions
    personal_suggestions = [
        "Create a meal plan for me",
        "How are my glucose levels looking?", 
        "What exercise is best for my diabetes type?",
        "Remind me about my medications",
        "Update my profile"
    ]
    
    print(f"\n💡 Try these personalized features:")
    for suggestion in personal_suggestions[:3]:
        if language_code != 'en':
            translated = bot.translate_response(suggestion, language_code)
            print(f"   • {translated}")
        else:
            print(f"   • {suggestion}")
    
    exit_instruction = "Type 'quit' to exit"
    if language_code != 'en':
        exit_instruction = bot.translate_response(exit_instruction, language_code)
    print(f"\n{exit_instruction}")
    
    try:
        while True:
            user_input = input(f"\n😊 You: ").strip()
            
            if bot.handle_exit_commands(user_input, language_code):
                if bot.patient_profile:
                    name = bot.patient_profile.get('name', 'there')
                    farewell = f"Take care, {name}! Keep up the great work managing your diabetes. I'll be here whenever you need personalized support! 🌟"
                else:
                    farewell = bot.get_cultural_farewell(language_code)
                
                if language_code != 'en':
                    farewell = bot.translate_response(farewell, language_code)
                print(f"\n💙 GlucoMate: {farewell}")
                break
            
            if user_input:
                response = bot.personalized_chat(user_input, language_code)
                print(f"\n👤 GlucoMate: {response}")
                print("\n" + "─" * 60)
            else:
                ready_msg = "I'm here with personalized care whenever you need me!"
                if language_code != 'en':
                    ready_msg = bot.translate_response(ready_msg, language_code)
                print(f"💭 {ready_msg}")
                
    except KeyboardInterrupt:
        if bot.patient_profile:
            name = bot.patient_profile.get('name', 'there')
            farewell = f"Take care, {name}! 🌟"
        else:
            farewell = "Take care! 🌟"
        print(f"\n\n💙 GlucoMate: {farewell}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
    finally:
        bot.conversation_active = False

if __name__ == "__main__":
    main()
