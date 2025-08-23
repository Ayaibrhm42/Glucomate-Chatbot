import boto3
import json
import sys
import os
import sqlite3
from datetime import datetime, timedelta
import threading
import time
from dotenv import load_dotenv
from googleapiclient.discovery import build
import re
from medical_safety import MedicalSafetyGuardrails

# Load environment variables
load_dotenv()

class PatientDatabase:
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        # Glucose readings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS glucose_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                reading REAL,
                timestamp TIMESTAMP,
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
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_patient_profile(self, patient_id):
        """Get complete patient profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM patient_profile WHERE patient_id = ?', (patient_id,))
        profile = cursor.execute('SELECT * FROM patient_profile WHERE patient_id = ?', (patient_id,)).fetchone()
        
        if profile:
            columns = [desc[0] for desc in cursor.description]
            profile_dict = dict(zip(columns, profile))
            
            # Get medications
            cursor.execute('SELECT * FROM medications WHERE patient_id = ? AND active = 1', (patient_id,))
            medications = cursor.fetchall()
            
            # Get meal preferences
            cursor.execute('SELECT * FROM meal_preferences WHERE patient_id = ?', (patient_id,))
            meal_prefs = cursor.fetchone()
            
            # Get recent glucose readings
            cursor.execute('''SELECT * FROM glucose_readings WHERE patient_id = ? 
                             ORDER BY timestamp DESC LIMIT 10''', (patient_id,))
            recent_readings = cursor.fetchall()
            
            profile_dict['medications'] = medications
            profile_dict['meal_preferences'] = meal_prefs
            profile_dict['recent_readings'] = recent_readings
        
        conn.close()
        return profile_dict if profile else None

class PersonalizedGlucoMate:
    def __init__(self, patient_id=None):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        self.translate_client = boto3.client('translate', region_name='us-east-1')
        self.safety = MedicalSafetyGuardrails()
        self.model_id = "amazon.titan-text-premier-v1:0"
        
        # Patient data
        self.patient_db = PatientDatabase()
        self.patient_id = patient_id
        self.patient_profile = None
        self.medication_timer = None
        self.conversation_active = False
        
        # Chat-based profile collection state
        self.collecting_profile = False
        self.profile_questions = []
        self.current_question_index = 0
        self.temp_profile_data = {}
        self.original_request = None  # Store what they originally asked for
        
        if patient_id:
            self.load_patient_data()
            self.start_medication_monitoring()
        
        # Get credentials from environment variables
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = os.getenv('SEARCH_ENGINE_ID')
        self.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID', 'GXJOYBIHCU')
        
        # Initialize Google Search
        try:
            if self.google_api_key:
                self.search_service = build("customsearch", "v1", developerKey=self.google_api_key)
                print("🔍 Connected to trusted medical sources")
            else:
                self.search_service = None
                print("💭 Using knowledge base only")
        except Exception as e:
            self.search_service = None
            print("💭 Search temporarily unavailable - using medical knowledge base")
        
        # Supported languages
        self.supported_languages = {
            '1': ('English', 'en'),
            '2': ('Arabic', 'ar'), 
            '3': ('French', 'fr'),
            '4': ('Spanish', 'es'),
            '5': ('Portuguese', 'pt'),
            '6': ('German', 'de')
        }
        
        # Profile questions for chat collection
        self.medical_form_questions = [
            {
                "field": "diabetes_type",
                "question": "What type of diabetes do you have? (Type 1, Type 2, or Gestational)",
                "required": True
            },
            {
                "field": "age", 
                "question": "What's your age?",
                "required": True
            },
            {
                "field": "weight",
                "question": "What's your current weight in kg? (You can say 'skip' if you prefer not to share)",
                "required": False
            },
            {
                "field": "activity_level",
                "question": "How would you describe your activity level? (Sedentary, Light, Moderate, Active, Very Active)",
                "required": True
            },
            {
                "field": "dietary_restrictions",
                "question": "Do you have any dietary restrictions or preferences? (Vegetarian, Vegan, Halal, Kosher, None, etc.)",
                "required": False
            },
            {
                "field": "allergies",
                "question": "Do you have any food allergies I should know about? (You can say 'none' if not)",
                "required": False
            },
            {
                "field": "cultural_preferences",
                "question": "Any cultural or regional food preferences? (Mediterranean, Asian, Latin, etc.)",
                "required": False
            },
            {
                "field": "budget_range", 
                "question": "What's your grocery budget range? (Low, Moderate, High)",
                "required": False
            }
        ]
        
        # Encouraging phrases
        self.encouragement = [
            "You're taking a positive step by learning about your health.",
            "It's wonderful that you're being proactive about your diabetes care.",
            "Taking control of your diabetes is empowering - you're on the right track.",
            "Every small step towards better health matters.",
            "You're not alone in this journey - many people successfully manage diabetes."
        ]
    
    def check_profile_completeness(self):
        """Check if patient has enough data for personalization"""
        if not self.patient_profile:
            return {"complete": False, "missing": "all"}
        
        # Essential fields for personalization
        essential_fields = ['diabetes_type', 'age', 'activity_level']
        missing_fields = []
        
        for field in essential_fields:
            if not self.patient_profile.get(field):
                missing_fields.append(field)
        
        return {
            "complete": len(missing_fields) == 0,
            "missing": missing_fields,
            "has_some_data": len(missing_fields) < len(essential_fields)
        }
    
    def generate_general_meal_plan(self):
        """Generate a general meal plan when no profile data available"""
        general_prompt = """
        Create a general diabetes-friendly meal plan suitable for most people with diabetes:
        
        Please create a 3-day meal plan that:
        1. Is suitable for both Type 1 and Type 2 diabetes
        2. Includes breakfast, lunch, dinner, and 2 snacks per day
        3. Has moderate carb counts (30-45g per meal, 15g per snack)
        4. Uses common, accessible ingredients
        5. Includes simple preparation instructions
        6. Provides a basic grocery shopping list
        7. Offers tips for blood sugar management
        
        Make it practical and encouraging for someone just starting to manage their diabetes diet.
        """
        
        response = self.call_bedrock_model(general_prompt)
        
        # Add personalization offer
        offer_personalization = """
        
        📋 This is a general meal plan that works well for most people with diabetes. 
        
        🎯 **Want something more personalized?** I can create a custom meal plan based on your specific diabetes type, food preferences, activity level, and dietary needs! 
        
        Would you like me to ask you a few quick questions to make this more tailored to you? It will only take 2-3 minutes and I'll save the info for future conversations!
        
        Just say "yes, personalize it" or "make it personal" and I'll guide you through it! 📝
        """
        
        return response + offer_personalization
    
    def start_profile_collection(self, original_request):
        """Start collecting profile data through chat"""
        self.collecting_profile = True
        self.current_question_index = 0
        self.temp_profile_data = {}
        self.original_request = original_request
        
        welcome_msg = """
        Great! I'll ask you a few quick questions to personalize your diabetes care. This information will be securely saved to your profile so I can give you better recommendations in the future.
        
        You can say 'skip' for any question you don't want to answer, or 'stop' if you want to quit and use the general recommendations instead.
        
        Let's get started! 🚀
        """
        
        first_question = self.get_current_question()
        return welcome_msg + "\n\n" + first_question
    
    def get_current_question(self):
        """Get the current question in the profile collection flow"""
        if self.current_question_index < len(self.medical_form_questions):
            question_data = self.medical_form_questions[self.current_question_index]
            required_text = " (Required)" if question_data["required"] else " (Optional)"
            return f"**Question {self.current_question_index + 1}/{len(self.medical_form_questions)}**{required_text}: {question_data['question']}"
        return None
    
    def process_profile_answer(self, user_input):
        """Process an answer during profile collection"""
        user_input_lower = user_input.lower().strip()
        
        # Check for stop commands
        if user_input_lower in ['stop', 'quit', 'cancel', 'nevermind']:
            self.collecting_profile = False
            return "No problem! I'll use general recommendations for now. You can always set up your profile later. Let me get back to your original question..."
        
        # Get current question data
        if self.current_question_index >= len(self.medical_form_questions):
            return self.complete_profile_collection()
        
        current_question = self.medical_form_questions[self.current_question_index]
        field_name = current_question["field"]
        
        # Handle skip for optional questions
        if user_input_lower == 'skip' and not current_question["required"]:
            self.temp_profile_data[field_name] = None
        elif user_input_lower == 'skip' and current_question["required"]:
            return f"This question is required for personalization. {current_question['question']}"
        else:
            # Validate and store the answer
            validated_answer = self.validate_answer(field_name, user_input)
            if validated_answer["valid"]:
                self.temp_profile_data[field_name] = validated_answer["value"]
            else:
                return f"I didn't quite understand that. {validated_answer['error']} Please try again: {current_question['question']}"
        
        # Move to next question
        self.current_question_index += 1
        
        # Check if we have more questions
        if self.current_question_index < len(self.medical_form_questions):
            next_question = self.get_current_question()
            progress = f"Thanks! ({self.current_question_index}/{len(self.medical_form_questions)} completed)\n\n"
            return progress + next_question
        else:
            return self.complete_profile_collection()
    
    def validate_answer(self, field_name, user_input):
        """Validate answers based on field type"""
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
                return {"valid": False, "error": "Please enter a valid age between 1 and 120."}
            except:
                return {"valid": False, "error": "Please enter your age as a number."}
        
        elif field_name == "weight":
            try:
                weight = float(user_input)
                if 20 <= weight <= 300:  # Reasonable weight range in kg
                    return {"valid": True, "value": weight}
                return {"valid": False, "error": "Please enter a weight between 20-300 kg."}
            except:
                return {"valid": False, "error": "Please enter your weight as a number."}
        
        elif field_name == "activity_level":
            activity_mapping = {
                "sedentary": "Sedentary", "sitting": "Sedentary", "inactive": "Sedentary",
                "light": "Light", "lightly active": "Light", "light activity": "Light",
                "moderate": "Moderate", "moderately active": "Moderate", "moderate activity": "Moderate",
                "active": "Active", "very active": "Very Active", "highly active": "Very Active"
            }
            normalized = user_input.lower()
            for key, value in activity_mapping.items():
                if key in normalized:
                    return {"valid": True, "value": value}
            return {"valid": False, "error": "Please choose from: Sedentary, Light, Moderate, Active, or Very Active."}
        
        else:
            # For text fields, just clean and return
            return {"valid": True, "value": user_input.strip() if user_input.strip() else None}
    
    def complete_profile_collection(self):
        """Complete the profile collection and save to database"""
        self.collecting_profile = False
        
        # Save to database (integrate with your existing database)
        self.save_profile_to_database()
        
        # Reload patient profile
        self.load_patient_data()
        
        completion_msg = """
        🎉 Perfect! I've saved your information to your profile. Now I can give you much more personalized recommendations!
        
        Your profile includes:
        """
        
        # Show what was collected
        for key, value in self.temp_profile_data.items():
            if value:
                readable_key = key.replace('_', ' ').title()
                completion_msg += f"✅ {readable_key}: {value}\n"
        
        completion_msg += "\nNow let me create that personalized meal plan for you! 🍽️\n\n"
        
        # Clear temp data
        self.temp_profile_data = {}
        
        # Generate the original request with new profile data
        if "meal plan" in self.original_request.lower():
            personalized_plan = self.generate_personalized_meal_plan()
            return completion_msg + personalized_plan
        else:
            return completion_msg + "What would you like to know about your diabetes management?"
    
    def save_profile_to_database(self):
        """Save collected profile data to your existing database"""
        if not self.patient_id or not self.temp_profile_data:
            return
        
        # This would integrate with your team's existing database
        conn = sqlite3.connect(self.patient_db.db_path)
        cursor = conn.cursor()
        
        # Update existing profile or create new one
        update_fields = []
        values = []
        
        for field, value in self.temp_profile_data.items():
            if value is not None:
                update_fields.append(f"{field} = ?")
                values.append(value)
        
        if update_fields:
            values.append(self.patient_id)
            query = f"""
                INSERT INTO patient_profile (patient_id, {', '.join(self.temp_profile_data.keys())})
                VALUES ({', '.join(['?' for _ in self.temp_profile_data.values()])})
                ON CONFLICT(patient_id) 
                DO UPDATE SET {', '.join(update_fields)}
            """
            
            # For SQLite compatibility, use INSERT OR REPLACE
            profile_values = [self.patient_id] + list(self.temp_profile_data.values())
            cursor.execute(f"""
                INSERT OR REPLACE INTO patient_profile 
                (patient_id, {', '.join(self.temp_profile_data.keys())})
                VALUES ({', '.join(['?' for _ in profile_values])})
            """, profile_values)
        
        conn.commit()
        conn.close()
        """Load patient data from database"""
        if self.patient_id:
            self.patient_profile = self.patient_db.get_patient_profile(self.patient_id)
            if self.patient_profile:
                print(f"👋 Welcome back, {self.patient_profile.get('name', 'there')}!")
    
    def start_medication_monitoring(self):
        """Start background thread for medication reminders"""
        if self.patient_profile and self.patient_profile.get('medications'):
            self.medication_timer = threading.Thread(target=self._medication_monitor, daemon=True)
            self.medication_timer.start()
    
    def _medication_monitor(self):
        """Background medication reminder checker"""
        while True:
            if self.conversation_active and self.patient_profile:
                reminder = self.check_medication_time()
                if reminder:
                    print(f"\n🔔 MEDICATION REMINDER: {reminder}")
                    # In a real app, this would interrupt the conversation
                    
            time.sleep(60)  # Check every minute
    
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
                        if time_slot == current_hour_minute:
                            return f"Time to take your {med_name}! 💊"
                except:
                    pass
        
        return None
    
    def generate_personalized_meal_plan(self):
        """Generate meal plan based on patient profile"""
        if not self.patient_profile:
            return "I'd love to create a personalized meal plan for you! Please complete your profile first."
        
        profile = self.patient_profile
        meal_prefs = profile.get('meal_preferences', {})
        
        meal_plan_prompt = f"""
        Create a personalized 3-day diabetes-friendly meal plan for this patient:
        
        Patient Profile:
        - Diabetes Type: {profile.get('diabetes_type', 'Not specified')}
        - Age: {profile.get('age', 'Not specified')}
        - Weight: {profile.get('weight', 'Not specified')} kg
        - Activity Level: {profile.get('activity_level', 'Moderate')}
        - Target Glucose: {profile.get('target_glucose_min', 80)}-{profile.get('target_glucose_max', 130)} mg/dL
        
        Dietary Information:
        - Dietary Restrictions: {profile.get('dietary_restrictions', 'None')}
        - Allergies: {profile.get('allergies', 'None')}
        - Preferred Foods: {meal_prefs.get('preferred_foods') if meal_prefs else 'Not specified'}
        - Cultural Preferences: {meal_prefs.get('cultural_preferences') if meal_prefs else 'Not specified'}
        - Budget: {meal_prefs.get('budget_range') if meal_prefs else 'Moderate'}
        - Cooking Skills: {meal_prefs.get('cooking_skills') if meal_prefs else 'Intermediate'}
        
        Recent Glucose Readings: {self._get_recent_glucose_summary()}
        
        Please create a detailed 3-day meal plan with:
        1. Breakfast, lunch, dinner, and 2 snacks per day
        2. Estimated carb counts for each meal
        3. Portion sizes
        4. Simple preparation instructions
        5. Grocery shopping list
        6. Tips for blood sugar management
        
        Make it personal, practical, and encouraging!
        """
        
        return self.call_bedrock_model(meal_plan_prompt)
    
    def _get_recent_glucose_summary(self):
        """Get summary of recent glucose readings"""
        if not self.patient_profile or not self.patient_profile.get('recent_readings'):
            return "No recent readings available"
        
        readings = self.patient_profile['recent_readings']
        if readings:
            avg_reading = sum(reading[2] for reading in readings) / len(readings)
            return f"Average of last {len(readings)} readings: {avg_reading:.1f} mg/dL"
        return "No recent readings"
    
    def classify_query_type(self, question):
        """Enhanced classification including personal requests"""
        question_lower = question.lower()
        
        # Personal/healthcare management requests
        personal_indicators = [
            "meal plan", "diet plan", "what should i eat", "food recommendations",
            "my glucose", "my readings", "my medication", "my profile",
            "remind me", "track my", "log my", "record my"
        ]
        
        # Casual conversation
        casual_indicators = [
            "hi", "hello", "hey", "how are you", "what's up", "thanks", "thank you",
            "good morning", "good afternoon", "good evening", "bye", "goodbye",
            "comment ça va", "ça va", "كيف حالك", "¿cómo estás"
        ]
        
        # Medical information requests
        medical_indicators = [
            "diabetes", "blood sugar", "glucose", "insulin", "medication", "diet",
            "exercise", "symptoms", "treatment", "doctor", "health", "medical"
        ]
        
        # Check for personal/personalized requests
        if any(personal in question_lower for personal in personal_indicators):
            return "personal"
        
        # Check for casual conversation
        if any(casual in question_lower for casual in casual_indicators):
            return "casual"
        
        # Check for medical information
        if any(med_word in question_lower for med_word in medical_indicators):
            current_keywords = ["latest", "recent", "new", "current", "2024", "2025"]
            if any(kw in question_lower for kw in current_keywords):
                return "current_medical"
            return "medical"
        
        return "medical"  # Default to medical
    
    def create_personalized_prompt(self, user_input, query_type, language="English"):
        """Create prompts that include patient context"""
        
        patient_context = ""
        if self.patient_profile:
            patient_context = f"""
            Patient Context:
            - Name: {self.patient_profile.get('name', 'Patient')}
            - Diabetes Type: {self.patient_profile.get('diabetes_type', 'Not specified')}
            - Age: {self.patient_profile.get('age', 'Not specified')}
            - Recent HbA1c: {self.patient_profile.get('hba1c', 'Not available')}%
            - Target Glucose Range: {self.patient_profile.get('target_glucose_min', 80)}-{self.patient_profile.get('target_glucose_max', 130)} mg/dL
            - Activity Level: {self.patient_profile.get('activity_level', 'Not specified')}
            - Recent Glucose Average: {self._get_recent_glucose_summary()}
            """
        
        if query_type == "personal":
            prompt = f"""You are GlucoMate, a personalized diabetes care assistant for this specific patient. 
            
            {patient_context}
            
            The patient asked: "{user_input}"
            
            Provide a personalized response that:
            1. Uses their specific medical data and preferences
            2. Addresses them by name when appropriate
            3. References their diabetes type, targets, and recent readings
            4. Gives specific, actionable advice based on their profile
            5. Is warm, encouraging, and personally relevant
            
            Respond in {language}:"""
            
        elif query_type == "casual":
            prompt = f"""You are GlucoMate, a friendly diabetes care assistant. Someone just said: "{user_input}"
            
            {patient_context if patient_context else ""}
            
            This seems like casual conversation. Respond naturally and conversationally. If you know the patient's name, you can use it naturally.
            
            Respond in {language} in a natural, conversational way:"""
        
        else:  # medical queries
            prompt = f"""You are GlucoMate, a personalized diabetes companion for this patient.
            
            {patient_context}
            
            The patient asked: "{user_input}"
            
            Provide medical information that's personalized to their specific situation, diabetes type, and current management. Reference their profile when relevant.
            
            Respond in {language}:"""
        
        return prompt
    
    def call_bedrock_model(self, prompt):
        try:
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 2048,
                    "temperature": 0.3,
                    "topP": 0.9,
                    "stopSequences": []
                }
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['results'][0]['outputText']
            
        except Exception as e:
            return f"I'm having trouble connecting right now. Please try again in a moment."
    
    def personalized_chat(self, user_input, target_language_code='en'):
        """Main chat function with smart profile handling"""
        self.conversation_active = True
        
        # If we're in the middle of collecting profile data, handle that first
        if self.collecting_profile:
            return self.process_profile_answer(user_input)
        
        # Check for medication reminder first
        med_reminder = self.check_medication_time()
        if med_reminder:
            reminder_msg = f"🔔 Hi! Before we continue our chat, {med_reminder} Don't forget to take it with water. Now, what were you asking about?"
            return reminder_msg
        
        # Translate to English for processing
        english_input = user_input if target_language_code == 'en' else user_input
        
        # Check for emergencies first
        safety_check = self.safety.check_emergency_situation(english_input)
        
        if safety_check['is_emergency']:
            emergency_msg = "🚨 I'm really concerned about what you're describing. This sounds like it could be a medical emergency. Please call 911 or go to your nearest emergency room right away. Your safety is the most important thing right now."
            return emergency_msg
        
        # Check for personalization requests
        personalization_triggers = [
            "yes, personalize it", "make it personal", "personalize it", 
            "yes please", "sure", "yes", "ok", "okay"
        ]
        
        # If they're responding to a personalization offer
        if any(trigger in english_input.lower() for trigger in personalization_triggers):
            # Check if we just offered personalization
            return self.start_profile_collection("meal plan")
        
        # Classify query type
        query_type = self.classify_query_type(english_input)
        
        # Handle meal plan requests with smart profile checking
        if "meal plan" in english_input.lower() or "diet plan" in english_input.lower() or "what should i eat" in english_input.lower():
            profile_status = self.check_profile_completeness()
            
            if profile_status["complete"]:
                # Full personalization available
                return self.generate_personalized_meal_plan()
            elif profile_status["has_some_data"]:
                # Partial personalization
                return self.generate_semi_personalized_meal_plan()
            else:
                # No profile data - offer general + personalization option
                return self.generate_general_meal_plan()
        
        # Get language name for prompt
        language_name = "English"
        for code, (name, lang_code) in self.supported_languages.items():
            if lang_code == target_language_code:
                language_name = name
                break
        
        # Handle casual conversation - instant response
        if query_type == "casual":
            prompt = self.create_personalized_prompt(english_input, query_type, language_name)
            response = self.call_bedrock_model(prompt)
            return response
        
        # For medical/personal queries
        print("💭 Let me check your profile and think about this...")
        
        prompt = self.create_personalized_prompt(english_input, query_type, language_name)
        response = self.call_bedrock_model(prompt)
        
        # Add encouragement for emotional keywords
        if any(word in english_input.lower() for word in ['scared', 'worried', 'difficult', 'hard', 'confused']):
            encouragement = "\n\n" + self.encouragement[hash(english_input) % len(self.encouragement)]
            response = response + encouragement
        
        # Add disclaimer for medical questions
        if query_type in ["medical", "current_medical"]:
            disclaimer = "\n\nDisclaimer: This personalized information is educational only. Always consult your healthcare provider for medical decisions."
            response = response + disclaimer
        
        return response
    
    def generate_semi_personalized_meal_plan(self):
        """Generate meal plan with partial profile data"""
        available_data = {k: v for k, v in self.patient_profile.items() if v is not None}
        
        prompt = f"""
        Create a semi-personalized diabetes meal plan based on this available patient information:
        {json.dumps(available_data, indent=2)}
        
        Create a practical 3-day meal plan that incorporates what we know about the patient while being generally suitable for diabetes management.
        """
        
        response = self.call_bedrock_model(prompt)
        
        # Offer to complete profile
        completion_offer = """
        
        💡 **Want even better personalization?** I notice your profile is missing some details that could help me create an even more tailored plan. 
        
        Would you like me to ask a few quick questions to complete your profile? This will help me give you better recommendations in the future!
        
        Say "complete my profile" if you'd like to do that! 📋
        """
        
        return response + completion_offer

# Demo patient data setup
def setup_demo_patient():
    """Set up a demo patient for testing"""
    db = PatientDatabase()
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Insert demo patient
    cursor.execute('''
        INSERT OR REPLACE INTO patient_profile 
        (patient_id, name, age, diabetes_type, hba1c, target_glucose_min, target_glucose_max, 
         weight, activity_level, dietary_restrictions, language_preference)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('demo_patient_1', 'Sarah Johnson', 34, 'Type 2', 7.2, 80, 130, 68.5, 'Moderate', 'Vegetarian', 'en'))
    
    # Insert demo medications
    cursor.execute('''
        INSERT OR REPLACE INTO medications 
        (patient_id, medication_name, dosage, frequency, time_slots)
        VALUES (?, ?, ?, ?, ?)
    ''', ('demo_patient_1', 'Metformin', '500mg', 'Twice daily', '["08:00", "20:00"]'))
    
    # Insert demo meal preferences
    cursor.execute('''
        INSERT OR REPLACE INTO meal_preferences
        (patient_id, preferred_foods, cultural_preferences, budget_range, cooking_skills)
        VALUES (?, ?, ?, ?, ?)
    ''', ('demo_patient_1', 'Mediterranean foods, quinoa, salmon', 'Mediterranean', 'Moderate', 'Intermediate'))
    
    # Insert demo glucose readings
    for i in range(5):
        reading = 95 + i * 5  # Sample readings
        timestamp = datetime.now() - timedelta(days=i)
        cursor.execute('''
            INSERT INTO glucose_readings (patient_id, reading, timestamp, meal_context)
            VALUES (?, ?, ?, ?)
        ''', ('demo_patient_1', reading, timestamp, 'Before breakfast'))
    
    conn.commit()
    conn.close()
    print("✅ Demo patient data created!")

def main():
    print("🏥 PersonalizedGlucoMate - Your AI Diabetes Companion")
    print("💡 Now with personalized meal plans, medication reminders, and patient data!")
    
    # Setup demo patient data
    setup_demo_patient()
    
    # Initialize with demo patient
    bot = PersonalizedGlucoMate(patient_id='demo_patient_1')
    
    print(f"\n🌍 Available languages:")
    for key, (lang_name, lang_code) in bot.supported_languages.items():
        print(f"{key}. {lang_name}")
    
    print(f"\n💫 Try these personalized features:")
    print("- 'Generate a meal plan for me'")
    print("- 'What should I eat based on my recent glucose levels?'") 
    print("- 'How are my glucose readings looking?'")
    print("- 'What's my target range again?'")
    print("- Regular diabetes questions work too!")
    
    print(f"\n💬 Start chatting! (Type 'bye' to exit)")
    
    try:
        while True:
            user_input = input("\n😊 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye', 'stop']:
                bot.conversation_active = False
                print(f"\n💙 GlucoMate: Take care, {bot.patient_profile.get('name', 'there')}! Keep up the great work managing your diabetes. See you soon! 🌟")
                break
            
            if user_input:
                response = bot.personalized_chat(user_input, 'en')
                print(f"\n💙 GlucoMate: {response}")
                print("\n" + "─" * 50)
            else:
                print("😊 I'm here whenever you're ready to chat!")
                
    except KeyboardInterrupt:
        print(f"\n\n💙 GlucoMate: Take care! Keep monitoring your health! 🌟")

if __name__ == "__main__":
    main()
