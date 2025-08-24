import boto3
import json
import sys
import os
import sqlite3
from datetime import datetime, timedelta
import threading
import time
import statistics
import re
from dotenv import load_dotenv
from googleapiclient.discovery import build
from medical_safety import MedicalSafetyGuardrails

# Load environment variables
load_dotenv()

class ChangeTrackingDatabase:
    def __init__(self, db_path="patient_tracking.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize change tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Weekly assessments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                week_date TEXT,
                glucose_frequency TEXT,
                range_compliance INTEGER,
                energy_level INTEGER,
                symptoms TEXT,
                medication_adherence INTEGER,
                lifestyle_changes TEXT,
                sleep_quality INTEGER,
                stress_level INTEGER,
                concerns TEXT,
                overall_feeling INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        # Progress milestones table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                milestone_type TEXT,
                milestone_title TEXT,
                description TEXT,
                achieved_date TEXT,
                value_achieved TEXT,
                celebrated BOOLEAN DEFAULT 0,
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        # Trend analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trend_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                analysis_date TEXT,
                trend_type TEXT,
                trend_direction TEXT,
                confidence_level REAL,
                description TEXT,
                recommendations TEXT,
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        # Habit tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS habit_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                habit_name TEXT,
                start_date TEXT,
                target_frequency TEXT,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                total_completions INTEGER DEFAULT 0,
                last_completed TEXT,
                active BOOLEAN DEFAULT 1,
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        # Conversation insights table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                conversation_date TEXT,
                detected_mood TEXT,
                health_concerns TEXT,
                progress_indicators TEXT,
                recommendations_given TEXT,
                follow_up_needed BOOLEAN DEFAULT 0,
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        conn.commit()
        conn.close()

class ChangeTrackingGlucoMate:
    def __init__(self, patient_id=None):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        self.translate_client = boto3.client('translate', region_name='us-east-1')
        self.safety = MedicalSafetyGuardrails()
        self.model_id = "amazon.titan-text-premier-v1:0"
        
        # Patient data
        self.patient_id = patient_id
        self.tracking_db = ChangeTrackingDatabase()
        self.conversation_active = False
        
        # Weekly check-in state
        self.in_weekly_checkin = False
        self.checkin_data = {}
        self.checkin_questions = [
            {
                "key": "glucose_frequency",
                "question": "How often did you check your glucose this week?",
                "options": ["1-2 times total", "3-4 times total", "Once daily", "2-3 times daily", "4+ times daily"],
                "type": "choice"
            },
            {
                "key": "range_compliance", 
                "question": "What percentage of your readings were in your target range this week?",
                "options": ["Less than 25%", "25-50%", "50-75%", "75-90%", "90%+", "Not sure"],
                "type": "choice"
            },
            {
                "key": "energy_level",
                "question": "On a scale of 1-10, how has your energy been this week compared to last week?",
                "options": ["1-2 (Much worse)", "3-4 (Worse)", "5-6 (About the same)", "7-8 (Better)", "9-10 (Much better)"],
                "type": "scale"
            },
            {
                "key": "sleep_quality",
                "question": "How has your sleep quality been this week?",
                "options": ["1-2 (Very poor)", "3-4 (Poor)", "5-6 (Fair)", "7-8 (Good)", "9-10 (Excellent)"],
                "type": "scale"
            },
            {
                "key": "medication_adherence",
                "question": "How consistently did you take your diabetes medications this week?",
                "options": ["Less than 50%", "50-70%", "70-85%", "85-95%", "95-100%", "I don't take medications"],
                "type": "choice"
            },
            {
                "key": "lifestyle_changes",
                "question": "Any changes to your routine this week? (diet, exercise, stress, work, etc.)",
                "type": "text"
            },
            {
                "key": "concerns",
                "question": "Any concerns or symptoms you've noticed this week?",
                "type": "text"
            }
        ]
        self.current_checkin_index = 0
        
        # Get credentials from environment variables
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = os.getenv('SEARCH_ENGINE_ID')
        self.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID', 'GXJOYBIHCU')
        
        # Achievement system
        self.milestones = {
            "first_week": {"title": "Getting Started", "description": "Completed first weekly check-in"},
            "consistency_streak": {"title": "Consistent Tracker", "description": "3 weeks of regular check-ins"},
            "improvement_trend": {"title": "Progress Champion", "description": "Improved energy levels for 2+ weeks"},
            "range_master": {"title": "Range Master", "description": "75%+ readings in target range"},
            "medication_hero": {"title": "Medication Hero", "description": "95%+ medication adherence for 4 weeks"},
            "lifestyle_warrior": {"title": "Lifestyle Warrior", "description": "Consistent healthy habits for 1 month"}
        }
        
        # Encouraging phrases
        self.encouragement = [
            "You're making real progress in managing your diabetes!",
            "Every small improvement matters - you're doing great!",
            "Your commitment to tracking your health is inspiring!",
            "These positive changes will benefit your long-term health!",
            "You're building habits that will serve you well!"
        ]
        
        # Initialize tracking for patient
        if patient_id:
            self.setup_change_tracking()
    
    def setup_change_tracking(self):
        """Initialize change tracking for patient"""
        # Check if it's time for weekly check-in
        self.check_weekly_checkin_due()
        
        # Initialize any needed habits or tracking
        self.initialize_habit_tracking()
    
    def check_weekly_checkin_due(self):
        """Check if weekly check-in is due"""
        conn = sqlite3.connect(self.tracking_db.db_path)
        cursor = conn.cursor()
        
        # Get last weekly assessment
        cursor.execute('''
            SELECT week_date FROM weekly_assessments 
            WHERE patient_id = ? ORDER BY week_date DESC LIMIT 1
        ''', (self.patient_id,))
        
        last_checkin = cursor.fetchone()
        conn.close()
        
        if not last_checkin:
            return True  # First time, check-in needed
        
        last_date = datetime.strptime(last_checkin[0], '%Y-%m-%d')
        days_since = (datetime.now() - last_date).days
        
        return days_since >= 7  # Weekly check-in
    
    def initialize_habit_tracking(self):
        """Set up habit tracking for new patients"""
        conn = sqlite3.connect(self.tracking_db.db_path)
        cursor = conn.cursor()
        
        # Check if habits already exist
        cursor.execute('SELECT COUNT(*) FROM habit_tracking WHERE patient_id = ?', (self.patient_id,))
        existing_habits = cursor.fetchone()[0]
        
        if existing_habits == 0:
            # Initialize common diabetes habits
            default_habits = [
                ("glucose_monitoring", "Daily glucose checking", "daily"),
                ("medication_taking", "Taking medications as prescribed", "daily"),
                ("exercise", "Regular physical activity", "3x_weekly"),
                ("meal_planning", "Following meal plan", "daily")
            ]
            
            for habit_name, description, frequency in default_habits:
                cursor.execute('''
                    INSERT INTO habit_tracking 
                    (patient_id, habit_name, start_date, target_frequency)
                    VALUES (?, ?, ?, ?)
                ''', (self.patient_id, habit_name, datetime.now().strftime('%Y-%m-%d'), frequency))
        
        conn.commit()
        conn.close()
    
    def detect_conversation_patterns(self, user_input):
        """Detect mood, concerns, and progress indicators from conversation"""
        user_input_lower = user_input.lower()
        
        # Mood detection
        positive_indicators = ['good', 'great', 'better', 'improving', 'feeling well', 'energy', 'stable']
        negative_indicators = ['tired', 'stressed', 'worried', 'worse', 'difficult', 'frustrated', 'confused']
        concern_indicators = ['high readings', 'low blood sugar', 'symptoms', 'dizzy', 'thirsty', 'blurred']
        
        detected_mood = "neutral"
        if any(indicator in user_input_lower for indicator in positive_indicators):
            detected_mood = "positive"
        elif any(indicator in user_input_lower for indicator in negative_indicators):
            detected_mood = "negative"
        
        health_concerns = []
        for concern in concern_indicators:
            if concern in user_input_lower:
                health_concerns.append(concern)
        
        # Save conversation insights
        self.save_conversation_insights(detected_mood, health_concerns, user_input)
        
        return {
            "mood": detected_mood,
            "concerns": health_concerns,
            "needs_followup": len(health_concerns) > 0 or detected_mood == "negative"
        }
    
    def save_conversation_insights(self, mood, concerns, original_input):
        """Save conversation insights to database"""
        conn = sqlite3.connect(self.tracking_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversation_insights 
            (patient_id, conversation_date, detected_mood, health_concerns, follow_up_needed)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            self.patient_id,
            datetime.now().strftime('%Y-%m-%d'),
            mood,
            ', '.join(concerns),
            len(concerns) > 0
        ))
        
        conn.commit()
        conn.close()
    
    def start_weekly_checkin(self):
        """Start weekly check-in process"""
        self.in_weekly_checkin = True
        self.current_checkin_index = 0
        self.checkin_data = {}
        
        intro_message = """
        🌟 Time for your weekly diabetes check-in! This helps me track your progress and give you better support.
        
        I'll ask you 7 quick questions about this week. You can say 'skip' for any question, or 'stop' to do this later.
        
        Let's see how you've been doing! 📊
        """
        
        first_question = self.get_current_checkin_question()
        return intro_message + "\n\n" + first_question
    
    def get_current_checkin_question(self):
        """Get current check-in question"""
        if self.current_checkin_index >= len(self.checkin_questions):
            return None
        
        question_data = self.checkin_questions[self.current_checkin_index]
        question_text = f"**Question {self.current_checkin_index + 1}/{len(self.checkin_questions)}**: {question_data['question']}"
        
        if question_data.get('options') and question_data['type'] != 'text':
            question_text += "\n\nOptions:"
            for i, option in enumerate(question_data['options'], 1):
                question_text += f"\n{i}. {option}"
            question_text += "\n\nJust tell me the number or describe your answer!"
        
        return question_text
    
    def process_checkin_answer(self, user_input):
        """Process check-in answer"""
        user_input_clean = user_input.strip().lower()
        
        # Handle stop/skip commands
        if user_input_clean in ['stop', 'quit', 'later', 'not now']:
            self.in_weekly_checkin = False
            return "No worries! I'll remind you about the weekly check-in later. You can say 'weekly check-in' anytime to start it. 😊"
        
        if user_input_clean == 'skip':
            # Skip current question
            self.checkin_data[self.checkin_questions[self.current_checkin_index]['key']] = None
        else:
            # Process the answer
            question_data = self.checkin_questions[self.current_checkin_index]
            processed_answer = self.process_answer_by_type(user_input, question_data)
            self.checkin_data[question_data['key']] = processed_answer
        
        # Move to next question
        self.current_checkin_index += 1
        
        if self.current_checkin_index >= len(self.checkin_questions):
            return self.complete_weekly_checkin()
        else:
            next_question = self.get_current_checkin_question()
            progress = f"Great! ({self.current_checkin_index}/{len(self.checkin_questions)} completed)\n\n"
            return progress + next_question
    
    def process_answer_by_type(self, user_input, question_data):
        """Process answer based on question type"""
        if question_data['type'] == 'text':
            return user_input.strip()
        
        elif question_data['type'] in ['choice', 'scale']:
            # Try to match number or text
            try:
                choice_num = int(user_input.strip())
                if 1 <= choice_num <= len(question_data['options']):
                    return question_data['options'][choice_num - 1]
            except:
                pass
            
            # Try to match text
            user_lower = user_input.lower()
            for option in question_data['options']:
                if user_lower in option.lower() or option.lower() in user_lower:
                    return option
            
            return user_input.strip()  # Return as-is if no match
    
    def complete_weekly_checkin(self):
        """Complete weekly check-in and analyze results"""
        self.in_weekly_checkin = False
        
        # Save to database
        self.save_weekly_assessment()
        
        # Generate insights
        insights = self.analyze_weekly_progress()
        
        # Check for milestones
        milestones = self.check_milestone_achievements()
        
        # Create response
        response = "🎉 Weekly check-in complete! Here's what I noticed:\n\n"
        response += insights
        
        if milestones:
            response += "\n\n🏆 **Achievements Unlocked:**\n"
            for milestone in milestones:
                response += f"• {milestone['title']}: {milestone['description']}\n"
        
        response += "\n\n📈 Keep up the great work! I'll check in with you again next week."
        
        return response
    
    def save_weekly_assessment(self):
        """Save weekly assessment to database"""
        conn = sqlite3.connect(self.tracking_db.db_path)
        cursor = conn.cursor()
        
        # Convert data for storage
        week_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO weekly_assessments 
            (patient_id, week_date, glucose_frequency, range_compliance, energy_level,
             symptoms, medication_adherence, lifestyle_changes, sleep_quality, concerns, overall_feeling)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.patient_id,
            week_date,
            self.checkin_data.get('glucose_frequency'),
            self.extract_numeric_value(self.checkin_data.get('range_compliance', ''), 50),
            self.extract_numeric_value(self.checkin_data.get('energy_level', ''), 5),
            self.checkin_data.get('symptoms', ''),
            self.extract_numeric_value(self.checkin_data.get('medication_adherence', ''), 85),
            self.checkin_data.get('lifestyle_changes', ''),
            self.extract_numeric_value(self.checkin_data.get('sleep_quality', ''), 5),
            self.checkin_data.get('concerns', ''),
            7  # Default overall feeling
        ))
        
        conn.commit()
        conn.close()
    
    def extract_numeric_value(self, text_response, default):
        """Extract numeric value from text response"""
        if not text_response:
            return default
        
        # Extract numbers from responses like "75-90%" or "7-8 (Better)"
        import re
        numbers = re.findall(r'\d+', str(text_response))
        if numbers:
            return int(numbers[0])
        return default
    
    def analyze_weekly_progress(self):
        """Analyze weekly progress and generate insights"""
        conn = sqlite3.connect(self.tracking_db.db_path)
        cursor = conn.cursor()
        
        # Get recent assessments for comparison
        cursor.execute('''
            SELECT * FROM weekly_assessments 
            WHERE patient_id = ? 
            ORDER BY week_date DESC LIMIT 4
        ''', (self.patient_id,))
        
        assessments = cursor.fetchall()
        conn.close()
        
        if len(assessments) < 2:
            return "📊 This is your first check-in! I'll be able to show you trends starting next week."
        
        # Compare current vs previous
        current = assessments[0]
        previous = assessments[1]
        
        insights = []
        
        # Energy level comparison
        if current[4] and previous[4]:  # energy_level index
            if current[4] > previous[4]:
                insights.append(f"✨ Your energy levels improved from {previous[4]}/10 to {current[4]}/10!")
            elif current[4] < previous[4]:
                insights.append(f"📉 Your energy dropped a bit from {previous[4]}/10 to {current[4]}/10. Let's explore what might help.")
            else:
                insights.append(f"📊 Your energy levels stayed consistent at {current[4]}/10.")
        
        # Range compliance comparison
        if current[3] and previous[3]:  # range_compliance index
            if current[3] > previous[3]:
                insights.append(f"🎯 Great progress! Your readings in target range improved from {previous[3]}% to {current[3]}%!")
            elif current[3] < previous[3]:
                insights.append(f"📈 Your target range percentage decreased from {previous[3]}% to {current[3]}%. We can work on strategies to improve this.")
        
        # Sleep quality
        if current[8] and previous[8]:  # sleep_quality index
            if current[8] > previous[8]:
                insights.append(f"😴 Your sleep quality improved! Better sleep often helps with glucose control.")
        
        return '\n'.join(insights) if insights else "📊 You're maintaining steady progress! Consistency is key in diabetes management."
    
    def check_milestone_achievements(self):
        """Check for new milestone achievements"""
        conn = sqlite3.connect(self.tracking_db.db_path)
        cursor = conn.cursor()
        
        # Count total assessments
        cursor.execute('SELECT COUNT(*) FROM weekly_assessments WHERE patient_id = ?', (self.patient_id,))
        total_assessments = cursor.fetchone()[0]
        
        milestones_earned = []
        
        # First week milestone
        if total_assessments == 1:
            self.save_milestone('first_week', 'Getting Started', 'Completed first weekly check-in')
            milestones_earned.append(self.milestones['first_week'])
        
        # Consistency streak
        if total_assessments == 3:
            self.save_milestone('consistency_streak', 'Consistent Tracker', '3 weeks of regular check-ins')
            milestones_earned.append(self.milestones['consistency_streak'])
        
        # Check for improvement trends
        cursor.execute('''
            SELECT energy_level FROM weekly_assessments 
            WHERE patient_id = ? 
            ORDER BY week_date DESC LIMIT 2
        ''', (self.patient_id,))
        
        recent_energy = cursor.fetchall()
        if len(recent_energy) == 2 and recent_energy[0][0] > recent_energy[1][0]:
            # Check if we haven't already given this milestone
            cursor.execute('''
                SELECT COUNT(*) FROM milestones 
                WHERE patient_id = ? AND milestone_type = 'improvement_trend'
            ''', (self.patient_id,))
            
            if cursor.fetchone()[0] == 0:
                self.save_milestone('improvement_trend', 'Progress Champion', 'Improved energy levels!')
                milestones_earned.append(self.milestones['improvement_trend'])
        
        conn.close()
        return milestones_earned
    
    def save_milestone(self, milestone_type, title, description):
        """Save milestone achievement"""
        conn = sqlite3.connect(self.tracking_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO milestones 
            (patient_id, milestone_type, milestone_title, description, achieved_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            self.patient_id,
            milestone_type,
            title,
            description,
            datetime.now().strftime('%Y-%m-%d')
        ))
        
        conn.commit()
        conn.close()
    
    def generate_trend_insights(self):
        """Generate insights from conversation and assessment trends"""
        conn = sqlite3.connect(self.tracking_db.db_path)
        cursor = conn.cursor()
        
        # Get recent mood trends
        cursor.execute('''
            SELECT detected_mood, conversation_date FROM conversation_insights 
            WHERE patient_id = ? 
            ORDER BY conversation_date DESC LIMIT 10
        ''', (self.patient_id,))
        
        mood_data = cursor.fetchall()
        
        # Get assessment trends
        cursor.execute('''
            SELECT energy_level, range_compliance, week_date FROM weekly_assessments 
            WHERE patient_id = ? 
            ORDER BY week_date DESC LIMIT 4
        ''', (self.patient_id,))
        
        assessment_data = cursor.fetchall()
        conn.close()
        
        insights = []
        
        if mood_data:
            positive_moods = sum(1 for mood in mood_data if mood[0] == 'positive')
            mood_percentage = (positive_moods / len(mood_data)) * 100
            
            if mood_percentage > 70:
                insights.append("🌟 You've been consistently positive in our conversations - that's wonderful!")
            elif mood_percentage < 30:
                insights.append("💙 I've noticed you might be going through a challenging time. I'm here to support you.")
        
        if len(assessment_data) >= 3:
            recent_energy = [a[0] for a in assessment_data[:3] if a[0]]
            if len(recent_energy) >= 3:
                if recent_energy[0] > recent_energy[1] > recent_energy[2]:
                    insights.append("📈 Your energy levels show a consistent upward trend - excellent progress!")
        
        return insights
    
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
    
    def smart_chat_with_tracking(self, user_input, target_language_code='en'):
        """Main chat function with comprehensive change tracking"""
        self.conversation_active = True
        
        # Handle weekly check-in process
        if self.in_weekly_checkin:
            return self.process_checkin_answer(user_input)
        
        # Check if user wants to start weekly check-in
        checkin_triggers = ['weekly check-in', 'check in', 'weekly update', 'progress check']
        if any(trigger in user_input.lower() for trigger in checkin_triggers):
            return self.start_weekly_checkin()
        
        # Auto-trigger weekly check-in if due
        if self.check_weekly_checkin_due():
            reminder = """
            🌟 Hey! It's been a week since our last check-in. I'd love to hear how you've been doing with your diabetes management!
            
            Would you like to do a quick weekly check-in now? It only takes 2-3 minutes and helps me give you better support. 
            
            Say 'yes' to start the check-in, or 'later' if you'd prefer to do it another time. 😊
            """
            return reminder
        
        # Detect patterns in conversation
        conversation_patterns = self.detect_conversation_patterns(user_input)
        
        # Check for emergencies first
        safety_check = self.safety.check_emergency_situation(user_input)
        
        if safety_check['is_emergency']:
            emergency_msg = "🚨 I'm really concerned about what you're describing. This sounds like it could be a medical emergency. Please call 911 or go to your nearest emergency room right away. Your safety is the most important thing right now."
            return emergency_msg
        
        # Generate contextual response with tracking insights
        response = self.generate_tracked_response(user_input, conversation_patterns, target_language_code)
        
        # Add trend insights if relevant
        if conversation_patterns['mood'] == 'positive':
            recent_insights = self.generate_trend_insights()
            if recent_insights:
                response += "\n\n" + "\n".join(recent_insights)
        
        # Add encouragement for concerning patterns
        if conversation_patterns['needs_followup']:
            encouragement = "\n\n" + self.encouragement[hash(user_input) % len(self.encouragement)]
            response += encouragement
        
        return response
    
    def generate_tracked_response(self, user_input, patterns, language_code):
        """Generate response incorporating tracking insights"""
        
        # Get recent assessment data for context
        conn = sqlite3.connect(self.tracking_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT energy_level, range_compliance, sleep_quality FROM weekly_assessments 
            WHERE patient_id = ? ORDER BY week_date DESC LIMIT 1
        ''', (self.patient_id,))
        
        recent_assessment = cursor.fetchone()
        conn.close()
        
        # Create context-aware prompt
        tracking_context = ""
        if recent_assessment:
            energy, glucose_range, sleep = recent_assessment
            tracking_context = f"""
            Patient's Recent Progress Context:
            - Recent energy level: {energy}/10
            - Recent glucose control: {glucose_range}% in target range
            - Recent sleep quality: {sleep}/10
            - Current mood in conversation: {patterns['mood']}
            """
        
        # Create personalized prompt
        prompt = f"""You are GlucoMate, a caring diabetes companion who tracks patient progress over time.

        {tracking_context}
        
        Patient said: "{user_input}"
        
        Respond in a way that:
        1. Acknowledges their progress and patterns you're tracking
        2. References their recent improvements or challenges naturally
        3. Provides relevant, personalized advice
        4. Shows you remember their journey and celebrate their wins
        5. Is encouraging and supportive
        6. Connects their current question to their overall progress
        
        Be warm, personal, and show that you're truly tracking their diabetes journey with them.
        """
        
        return self.call_bedrock_model(prompt)

def main():
    """Demo of change tracking system"""
    print("🏥 GlucoMate with Advanced Change Tracking")
    print("📊 Now tracking progress, milestones, and trends!")
    
    # Initialize with demo patient
    bot = ChangeTrackingGlucoMate(patient_id='demo_patient_tracking')
    
    print(f"\n🌟 New Features:")
    print("• Weekly check-ins to track your progress")
    print("• Milestone achievements and celebrations")  
    print("• Trend analysis from conversations")
    print("• Personalized insights based on your journey")
    
    print(f"\n💬 Try saying:")
    print("• 'How am I doing?' - Get progress insights")
    print("• 'Weekly check-in' - Start weekly assessment")
    print("• 'I'm feeling much better lately' - Positive progress tracking")
    print("• 'My energy is low today' - Concern detection")
    
    print(f"\n✨ Start chatting! (Type 'bye' to exit)")
    
    try:
        while True:
            user_input = input("\n😊 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye', 'stop']:
                bot.conversation_active = False
                
                # Generate farewell with progress summary
                conn = sqlite3.connect(bot.tracking_db.db_path)
                cursor = conn.cursor()
                
                # Get milestone count
                cursor.execute('SELECT COUNT(*) FROM milestones WHERE patient_id = ?', (bot.patient_id,))
                milestone_count = cursor.fetchone()[0]
                
                # Get assessment count  
                cursor.execute('SELECT COUNT(*) FROM weekly_assessments WHERE patient_id = ?', (bot.patient_id,))
                assessment_count = cursor.fetchone()[0]
                
                conn.close()
                
                farewell = f"""
💙 Take care! Here's a quick summary of your progress:
• {assessment_count} weekly check-ins completed
• {milestone_count} milestones achieved
• Continuous progress tracking and insights

Keep up the amazing work with your diabetes management! I'll be here whenever you need support. 🌟
                """
                
                print(f"\n💙 GlucoMate: {farewell}")
                break
            
            if user_input:
                response = bot.smart_chat_with_tracking(user_input, 'en')
                print(f"\n💙 GlucoMate: {response}")
                print("\n" + "─" * 50)
            else:
                print("😊 I'm here whenever you're ready to chat!")
                
    except KeyboardInterrupt:
        print(f"\n\n💙 GlucoMate: Take care! Keep tracking your progress! 🌟")

if __name__ == "__main__":
    main()
