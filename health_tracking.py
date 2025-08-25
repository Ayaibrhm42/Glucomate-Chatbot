"""
GlucoMate Level 6: Comprehensive Health Tracking
Inherits: Bedrock core, safety, multilingual, knowledge base, smart search, personalization
Adds: Weekly check-ins, progress tracking, milestone achievements, trend analysis
"""

import boto3
import json
import sys
import os
import sqlite3
import statistics
from datetime import datetime, timedelta
from personalized_glucomate import PersonalizedGlucoMate, PatientDatabase

class HealthTrackingDatabase(PatientDatabase):
    """Extended database handler for health tracking features"""
    
    def __init__(self, db_path="patient_data.db"):
        super().__init__(db_path)
        self.init_tracking_tables()
    
    def init_tracking_tables(self):
        """Initialize health tracking tables"""
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
                sleep_quality INTEGER,
                medication_adherence INTEGER,
                lifestyle_changes TEXT,
                symptoms TEXT,
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patient_profile (patient_id)
            )
        ''')
        
        conn.commit()
        conn.close()

class HealthTrackingGlucoMate(PersonalizedGlucoMate):
    """
    Level 6: Adds comprehensive health tracking and progress monitoring
    Inherits: ALL previous features (Bedrock, safety, multilingual, knowledge, search, personalization)
    Adds: Weekly check-ins, progress tracking, milestone achievements, trend analysis
    """
    
    def __init__(self, patient_id=None):
        # Initialize with tracking database
        temp_db_path = "patient_data.db" if patient_id else "patient_data.db"
        
        # Override the parent's database with tracking-enabled version
        super().__init__(patient_id)
        self.patient_db = HealthTrackingDatabase(temp_db_path)
        
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
                "question": "On a scale of 1-10, how has your energy been this week?",
                "options": ["1-2 (Much worse)", "3-4 (Worse)", "5-6 (About the same)", "7-8 (Better)", "9-10 (Much better)"],
                "type": "scale"
            },
            {
                "key": "sleep_quality",
                "question": "How has your sleep quality been this week (1-10)?",
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
                "key": "concerns",
                "question": "Any concerns or symptoms you've noticed this week?",
                "type": "text"
            }
        ]
        self.current_checkin_index = 0
        
        # Achievement system
        self.milestones = {
            "first_week": {"title": "Getting Started", "description": "Completed first weekly check-in"},
            "consistency_streak": {"title": "Consistent Tracker", "description": "3 weeks of regular check-ins"},
            "improvement_trend": {"title": "Progress Champion", "description": "Improved energy levels for 2+ weeks"},
            "range_master": {"title": "Range Master", "description": "75%+ readings in target range"},
            "medication_hero": {"title": "Medication Hero", "description": "95%+ medication adherence for 4 weeks"},
            "energy_boost": {"title": "Energy Booster", "description": "Energy levels improved significantly"}
        }
        
        # Initialize tracking for existing patient
        if patient_id and self.patient_profile:
            self.setup_health_tracking()
        
        print("📊 GlucoMate Level 6: Comprehensive health tracking loaded")
    
    def setup_health_tracking(self):
        """Initialize health tracking for patient"""
        self.check_weekly_checkin_due()
        self.initialize_habit_tracking()
    
    def check_weekly_checkin_due(self):
        """Check if weekly check-in is due"""
        conn = sqlite3.connect(self.patient_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT week_date FROM weekly_assessments 
            WHERE patient_id = ? ORDER BY week_date DESC LIMIT 1
        ''', (self.patient_id,))
        
        last_checkin = cursor.fetchone()
        conn.close()
        
        if not last_checkin:
            return True  # First time, check-in needed
        
        try:
            last_date = datetime.strptime(last_checkin[0], '%Y-%m-%d')
            days_since = (datetime.now() - last_date).days
            return days_since >= 7  # Weekly check-in
        except:
            return True  # If date parsing fails, assume check-in needed
    
    def initialize_habit_tracking(self):
        """Set up habit tracking for patients"""
        conn = sqlite3.connect(self.patient_db.db_path)
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
        positive_indicators = ['good', 'great', 'better', 'improving', 'feeling well', 'energy', 'stable', 'happy', 'motivated']
        negative_indicators = ['tired', 'stressed', 'worried', 'worse', 'difficult', 'frustrated', 'confused', 'sad', 'overwhelmed']
        concern_indicators = ['high readings', 'low blood sugar', 'symptoms', 'dizzy', 'thirsty', 'blurred', 'pain', 'numb']
        
        detected_mood = "neutral"
        if any(indicator in user_input_lower for indicator in positive_indicators):
            detected_mood = "positive"
        elif any(indicator in user_input_lower for indicator in negative_indicators):
            detected_mood = "negative"
        
        health_concerns = [concern for concern in concern_indicators if concern in user_input_lower]
        
        # Progress indicators
        progress_indicators = []
        if any(word in user_input_lower for word in ['lost weight', 'better control', 'improved', 'stable']):
            progress_indicators.append('improvement')
        if any(word in user_input_lower for word in ['exercise', 'walking', 'gym', 'active']):
            progress_indicators.append('exercise')
        
        # Save conversation insights
        self.save_conversation_insights(detected_mood, health_concerns, progress_indicators, user_input)
        
        return {
            "mood": detected_mood,
            "concerns": health_concerns,
            "progress": progress_indicators,
            "needs_followup": len(health_concerns) > 0 or detected_mood == "negative"
        }
    
    def save_conversation_insights(self, mood, concerns, progress_indicators, original_input):
        """Save conversation insights to database"""
        if not self.patient_id:
            return
        
        conn = sqlite3.connect(self.patient_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversation_insights 
            (patient_id, conversation_date, detected_mood, health_concerns, progress_indicators, follow_up_needed)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            self.patient_id,
            datetime.now().strftime('%Y-%m-%d'),
            mood,
            ', '.join(concerns),
            ', '.join(progress_indicators),
            len(concerns) > 0
        ))
        
        conn.commit()
        conn.close()
    
    def start_weekly_checkin(self):
        """Start weekly check-in process"""
        self.in_weekly_checkin = True
        self.current_checkin_index = 0
        self.checkin_data = {}
        
        patient_name = self.patient_profile.get('name', 'there') if self.patient_profile else 'there'
        
        intro_message = f"""
        🌟 Hi {patient_name}! Time for your weekly diabetes check-in. This helps me track your progress and celebrate your wins!
        
        I'll ask you 6 quick questions about this week. You can say 'skip' for any question, or 'stop' to do this later.
        
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
        patient_name = self.patient_profile.get('name', 'friend') if self.patient_profile else 'friend'
        
        response = f"🎉 Weekly check-in complete, {patient_name}! Here's what I noticed:\n\n"
        response += insights
        
        if milestones:
            response += "\n\n🏆 **Achievements Unlocked:**\n"
            for milestone in milestones:
                response += f"• {milestone['title']}: {milestone['description']}\n"
        
        response += "\n\n📈 Keep up the great work! I'll check in with you again next week."
        
        return response
    
    def save_weekly_assessment(self):
        """Save weekly assessment to database"""
        if not self.patient_id:
            return
        
        conn = sqlite3.connect(self.patient_db.db_path)
        cursor = conn.cursor()
        
        # Convert data for storage
        week_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO weekly_assessments 
            (patient_id, week_date, glucose_frequency, range_compliance, energy_level,
             sleep_quality, medication_adherence, concerns, overall_feeling)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.patient_id,
            week_date,
            self.checkin_data.get('glucose_frequency'),
            self.extract_numeric_value(self.checkin_data.get('range_compliance', ''), 50),
            self.extract_numeric_value(self.checkin_data.get('energy_level', ''), 5),
            self.extract_numeric_value(self.checkin_data.get('sleep_quality', ''), 5),
            self.extract_numeric_value(self.checkin_data.get('medication_adherence', ''), 85),
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
        if not self.patient_id:
            return "📊 Check-in completed! Great job staying on top of your health."
        
        conn = sqlite3.connect(self.patient_db.db_path)
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
        
        # Energy level comparison (index 4 in database)
        if current[4] and previous[4]:
            if current[4] > previous[4]:
                insights.append(f"✨ Your energy levels improved from {previous[4]}/10 to {current[4]}/10!")
            elif current[4] < previous[4]:
                insights.append(f"📉 Your energy dropped a bit from {previous[4]}/10 to {current[4]}/10. Let's explore what might help.")
            else:
                insights.append(f"📊 Your energy levels stayed consistent at {current[4]}/10.")
        
        # Range compliance comparison (index 3)
        if current[3] and previous[3]:
            if current[3] > previous[3]:
                insights.append(f"🎯 Great progress! Your readings in target range improved from {previous[3]}% to {current[3]}%!")
            elif current[3] < previous[3]:
                insights.append(f"📈 Your target range percentage decreased from {previous[3]}% to {current[3]}%. We can work on strategies to improve this.")
        
        # Sleep quality (index 5)
        if current[5] and previous[5]:
            if current[5] > previous[5]:
                insights.append(f"😴 Your sleep quality improved! Better sleep often helps with glucose control.")
        
        # Add encouragement
        positive_changes = sum(1 for insight in insights if '✨' in insight or '🎯' in insight or '😴' in insight)
        if positive_changes >= 2:
            insights.append("🌟 You're making excellent progress in multiple areas - keep it up!")
        
        return '\n'.join(insights) if insights else "📊 You're maintaining steady progress! Consistency is key in diabetes management."
    
    def check_milestone_achievements(self):
        """Check for new milestone achievements"""
        if not self.patient_id:
            return []
        
        conn = sqlite3.connect(self.patient_db.db_path)
        cursor = conn.cursor()
        
        # Count total assessments
        cursor.execute('SELECT COUNT(*) FROM weekly_assessments WHERE patient_id = ?', (self.patient_id,))
        total_assessments = cursor.fetchone()[0]
        
        milestones_earned = []
        
        # First week milestone
        if total_assessments == 1:
            if self.save_milestone('first_week', 'Getting Started', 'Completed first weekly check-in'):
                milestones_earned.append(self.milestones['first_week'])
        
        # Consistency streak
        if total_assessments == 3:
            if self.save_milestone('consistency_streak', 'Consistent Tracker', '3 weeks of regular check-ins'):
                milestones_earned.append(self.milestones['consistency_streak'])
        
        # Check for improvement trends
        cursor.execute('''
            SELECT energy_level FROM weekly_assessments 
            WHERE patient_id = ? 
            ORDER BY week_date DESC LIMIT 2
        ''', (self.patient_id,))
        
        recent_energy = cursor.fetchall()
        if len(recent_energy) == 2 and recent_energy[0][0] and recent_energy[1][0]:
            if recent_energy[0][0] > recent_energy[1][0] + 1:  # Significant improvement
                cursor.execute('''
                    SELECT COUNT(*) FROM milestones 
                    WHERE patient_id = ? AND milestone_type = 'improvement_trend'
                ''', (self.patient_id,))
                
                if cursor.fetchone()[0] == 0:
                    if self.save_milestone('improvement_trend', 'Progress Champion', 'Improved energy levels!'):
                        milestones_earned.append(self.milestones['improvement_trend'])
        
        # Range compliance milestone
        cursor.execute('''
            SELECT range_compliance FROM weekly_assessments 
            WHERE patient_id = ? 
            ORDER BY week_date DESC LIMIT 1
        ''', (self.patient_id,))
        
        recent_compliance = cursor.fetchone()
        if recent_compliance and recent_compliance[0] and recent_compliance[0] >= 75:
            cursor.execute('''
                SELECT COUNT(*) FROM milestones 
                WHERE patient_id = ? AND milestone_type = 'range_master'
            ''', (self.patient_id,))
            
            if cursor.fetchone()[0] == 0:
                if self.save_milestone('range_master', 'Range Master', '75%+ readings in target range'):
                    milestones_earned.append(self.milestones['range_master'])
        
        conn.close()
        return milestones_earned
    
    def save_milestone(self, milestone_type, title, description):
        """Save milestone achievement"""
        if not self.patient_id:
            return False
        
        conn = sqlite3.connect(self.patient_db.db_path)
        cursor = conn.cursor()
        
        try:
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
            return True
        except Exception as e:
            print(f"Error saving milestone: {e}")
            return False
        finally:
            conn.close()
    
    def generate_progress_report(self):
        """Generate comprehensive progress report"""
        if not self.patient_id:
            return "Set up your profile first to see progress insights!"
        
        conn = sqlite3.connect(self.patient_db.db_path)
        cursor = conn.cursor()
        
        # Get assessment count
        cursor.execute('SELECT COUNT(*) FROM weekly_assessments WHERE patient_id = ?', (self.patient_id,))
        assessment_count = cursor.fetchone()[0]
        
        # Get milestone count
        cursor.execute('SELECT COUNT(*) FROM milestones WHERE patient_id = ?', (self.patient_id,))
        milestone_count = cursor.fetchone()[0]
        
        # Get recent trends
        cursor.execute('''
            SELECT energy_level, range_compliance, sleep_quality 
            FROM weekly_assessments 
            WHERE patient_id = ? 
            ORDER BY week_date DESC LIMIT 4
        ''', (self.patient_id,))
        
        recent_data = cursor.fetchall()
        
        # Get conversation insights
        cursor.execute('''
            SELECT detected_mood FROM conversation_insights 
            WHERE patient_id = ? 
            ORDER BY conversation_date DESC LIMIT 10
        ''', (self.patient_id,))
        
        mood_data = cursor.fetchall()
        conn.close()
        
        # Build report
        patient_name = self.patient_profile.get('name', 'friend') if self.patient_profile else 'friend'
        
        report = f"""
        📊 **Progress Report for {patient_name}**
        
        **Tracking Summary:**
        • {assessment_count} weekly check-ins completed
        • {milestone_count} milestones achieved
        • Consistent engagement with diabetes management
        
        """
        
        # Add trends if enough data
        if len(recent_data) >= 2:
            energy_trend = self.calculate_trend([d[0] for d in recent_data if d[0]])
            if energy_trend == "improving":
                report += "📈 **Energy levels are trending upward - excellent progress!**\n"
            elif energy_trend == "stable":
                report += "📊 **Energy levels are stable - good consistency!**\n"
        
        # Add mood insights
        if mood_data:
            positive_moods = sum(1 for mood in mood_data if mood[0] == 'positive')
            mood_percentage = (positive_moods / len(mood_data)) * 100
            
            if mood_percentage > 60:
                report += "😊 **You've been consistently positive in our conversations - wonderful to see!**\n"
        
        report += """
        **Keep up the great work!** 🌟
        Your commitment to tracking and managing your diabetes is inspiring.
        """
        
        return report
    
    def calculate_trend(self, values):
        """Calculate if values are improving, declining, or stable"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Remove None values
        clean_values = [v for v in values if v is not None]
        if len(clean_values) < 2:
            return "insufficient_data"
        
        # Simple trend calculation
        recent_avg = statistics.mean(clean_values[:2]) if len(clean_values) >= 2 else clean_values[0]
        older_avg = statistics.mean(clean_values[2:]) if len(clean_values) > 2 else clean_values[-1]
        
        if recent_avg > older_avg + 0.5:
            return "improving"
        elif recent_avg < older_avg - 0.5:
            return "declining"
        else:
            return "stable"
    
    def comprehensive_chat(self, user_input, target_language_code='en', auto_detect=False):
        """
        Most comprehensive chat with ALL inherited features + tracking
        
        This integrates EVERYTHING from all 6 levels:
        - Bedrock core and safety (Level 1)
        - Multilingual support (Level 2) 
        - Knowledge base (Level 3)
        - Smart search (Level 4)
        - Personalization (Level 5)
        - Health tracking (Level 6)
        """
        
        # Handle weekly check-in process first
        if self.in_weekly_checkin:
            return self.process_checkin_answer(user_input)
        
        # Check for tracking-specific commands
        if "weekly check" in user_input.lower() or "check in" in user_input.lower():
            return self.start_weekly_checkin()
        
        if "progress report" in user_input.lower() or "how am i doing" in user_input.lower():
            return self.generate_progress_report()
        
        # Auto-suggest weekly check-in if due
        if self.patient_id and self.check_weekly_checkin_due():
            patient_name = self.patient_profile.get('name', 'there') if self.patient_profile else 'there'
            reminder = f"""
            🌟 Hi {patient_name}! It's been a week since our last check-in. 
            
            Would you like to do a quick weekly check-in? It helps me track your progress and celebrate your wins!
            
            Say 'yes' to start the check-in, or ask me anything else! 😊
            """
            return reminder
        
        # Detect conversation patterns for insights
        if self.patient_id:
            patterns = self.detect_conversation_patterns(user_input)
        
        # Use ALL inherited functionality for regular chat
        # This includes: safety, multilingual, knowledge base, search, personalization
        response = self.personalized_chat(user_input, target_language_code, auto_detect)
        
        # Add progress insights and encouragement based on patterns
        if self.patient_id and hasattr(self, 'patterns') and patterns.get('mood') == 'positive':
            encouragement = f"\n\n🌟 I love hearing positive updates from you! Your attitude makes a real difference in managing diabetes."
            response += encouragement
        
        return response

def setup_demo_tracking_patient():
    """Set up demo patient with some tracking history"""
    db = HealthTrackingDatabase()
    
    # Create patient profile
    demo_data = {
        'patient_id': 'demo_patient_tracking',
        'name': 'Alex Thompson',
        'age': 28,
        'diabetes_type': 'Type 1',
        'hba1c': 6.8,
        'target_glucose_min': 70,
        'target_glucose_max': 140,
        'activity_level': 'Active',
        'dietary_restrictions': 'None',
        'language_preference': 'en'
    }
    
    success = db.save_patient_profile(demo_data)
    
    if success:
        # Add some sample weekly assessments
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # Add 3 weeks of sample data
        sample_assessments = [
            ('2024-01-01', 'Once daily', 65, 6, 7, 90, 'Feeling good overall'),
            ('2024-01-08', '2-3 times daily', 70, 7, 8, 95, 'More energy this week'),
            ('2024-01-15', '2-3 times daily', 80, 8, 8, 95, 'Great week!')
        ]
        
        for week_date, glucose_freq, compliance, energy, sleep, med_adh, concerns in sample_assessments:
            cursor.execute('''
                INSERT INTO weekly_assessments 
                (patient_id, week_date, glucose_frequency, range_compliance, energy_level,
                 sleep_quality, medication_adherence, concerns, overall_feeling)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('demo_patient_tracking', week_date, glucose_freq, compliance, energy, sleep, med_adh, concerns, 8))
        
        conn.commit()
        conn.close()
        
        print("✅ Demo patient with tracking history created!")
    
    return 'demo_patient_tracking'

def main():
    """Demo of Level 6 - Complete Health Tracking GlucoMate"""
    print("📊 GlucoMate Level 6: Comprehensive Health Tracking System")
    print("🎯 The complete diabetes management companion with full progress tracking!")
    print("\n✨ All Features:")
    print("   • Weekly health check-ins and progress tracking")
    print("   • Milestone achievements and celebrations")
    print("   • Trend analysis and insights")
    print("   • Conversation mood and concern detection")
    print("   • Personalized care with patient profiles")
    print("   • Smart medical search and knowledge base")
    print("   • Full multilingual support")
    print("   • Comprehensive safety guardrails")
    
    # Set up demo patient with tracking history
    demo_patient_id = setup_demo_tracking_patient()
    
    bot = HealthTrackingGlucoMate(patient_id=demo_patient_id)
    
    # Show comprehensive stats
    if bot.patient_profile:
        profile = bot.patient_profile
        print(f"\n👤 Patient Profile:")
        print(f"   • Name: {profile.get('name', 'Not set')}")
        print(f"   • Diabetes Type: {profile.get('diabetes_type', 'Not set')}")
        print(f"   • Target Range: {profile.get('target_glucose_min', 80)}-{profile.get('target_glucose_max', 130)} mg/dL")
        
        # Show tracking stats
        conn = sqlite3.connect(bot.patient_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM weekly_assessments WHERE patient_id = ?', (demo_patient_id,))
        assessment_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM milestones WHERE patient_id = ?', (demo_patient_id,))
        milestone_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n📊 Tracking Stats:")
        print(f"   • Weekly Check-ins: {assessment_count}")
        print(f"   • Milestones Achieved: {milestone_count}")
        print(f"   • Health Tracking: Active")
    
    # Language selection (inherited from all previous levels)
    language_name, language_code = bot.get_language_choice()
    
    # Personalized greeting with tracking context
    if bot.patient_profile:
        name = bot.patient_profile.get('name', 'there')
        greeting = f"Hello {name}! I'm your complete diabetes care companion, ready to help with personalized advice and track your progress together."
    else:
        greeting = bot.get_cultural_greeting(language_code)
    
    if language_code != 'en':
        greeting = bot.translate_response(greeting, language_code)
    
    print(f"\n💙 {greeting}")
    
    # Comprehensive suggestions
    comprehensive_suggestions = [
        "How am I doing with my progress?",
        "Start my weekly check-in", 
        "Create a personalized meal plan",
        "What's the latest diabetes research?",
        "I'm feeling great about my control lately",
        "Help me understand my target range"
    ]
    
    print(f"\n💡 Try these comprehensive features:")
    for suggestion in comprehensive_suggestions[:4]:
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
                    farewell = f"Take care, {name}! Keep up the excellent work with your diabetes management. I'm so proud of your progress! 🌟"
                else:
                    farewell = bot.get_cultural_farewell(language_code)
                
                if language_code != 'en':
                    farewell = bot.translate_response(farewell, language_code)
                print(f"\n💙 GlucoMate: {farewell}")
                
                # Show final stats
                if bot.patient_id:
                    final_report = bot.generate_progress_report()
                    print(f"\n{final_report}")
                break
            
            if user_input:
                response = bot.comprehensive_chat(user_input, language_code, auto_detect=True)
                print(f"\n📊 GlucoMate: {response}")
                print("\n" + "─" * 60)
            else:
                ready_msg = "I'm here with comprehensive diabetes care and progress tracking!"
                if language_code != 'en':
                    ready_msg = bot.translate_response(ready_msg, language_code)
                print(f"💭 {ready_msg}")
                
    except KeyboardInterrupt:
        if bot.patient_profile:
            name = bot.patient_profile.get('name', 'there')
            farewell = f"Take care, {name}! Keep tracking your progress! 🌟"
        else:
            farewell = "Take care! Keep managing your diabetes well! 🌟"
        print(f"\n\n💙 GlucoMate: {farewell}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
    finally:
        bot.conversation_active = False

if __name__ == "__main__":
    main()
