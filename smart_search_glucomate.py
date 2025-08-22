import boto3
import json
import sys
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from datetime import datetime
import re
from medical_safety import MedicalSafetyGuardrails

# Load environment variables
load_dotenv()

class SmartMedicalSearchGlucoMate:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        self.translate_client = boto3.client('translate', region_name='us-east-1')
        self.safety = MedicalSafetyGuardrails()
        self.model_id = "amazon.titan-text-premier-v1:0"
        
        # Get credentials from environment variables
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = os.getenv('SEARCH_ENGINE_ID')
        self.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID', 'GXJOYBIHCU')
        
        # Initialize Google Search
        try:
            if self.google_api_key:
                self.search_service = build("customsearch", "v1", developerKey=self.google_api_key)
                print("Connected to trusted medical sources")
            else:
                self.search_service = None
                print("Using knowledge base only")
        except Exception as e:
            self.search_service = None
            print("Search temporarily unavailable - using medical knowledge base")
        
        # Supported languages
        self.supported_languages = {
            '1': ('English', 'en'),
            '2': ('Arabic', 'ar'), 
            '3': ('French', 'fr'),
            '4': ('Spanish', 'es'),
            '5': ('Portuguese', 'pt'),
            '6': ('German', 'de')
        }
        
        # Warm, human conversation starters
        self.conversation_starters = [
            "I understand you're looking for information about",
            "Let me help you with that question about",
            "That's a great question about",
            "I'm here to help you understand",
            "Let me share what I know about"
        ]
        
        # Encouraging phrases (no emojis)
        self.encouragement = [
            "You're taking a positive step by learning about your health.",
            "It's wonderful that you're being proactive about your diabetes care.",
            "Taking control of your diabetes is empowering - you're on the right track.",
            "Every small step towards better health matters.",
            "You're not alone in this journey - many people successfully manage diabetes."
        ]
    
    def classify_query_type(self, question):
        """Classify the type of user input"""
        question_lower = question.lower()
        
        # Simple classification - is it casual or medical?
        casual_indicators = [
            "hi", "hello", "hey", "how are you", "what's up", "thanks", "thank you",
            "good morning", "good afternoon", "good evening", "bye", "goodbye",
            "comment ça va", "ça va", "كيف حالك", "¿cómo estás"
        ]
        
        medical_indicators = [
            "diabetes", "blood sugar", "glucose", "insulin", "medication", "diet",
            "exercise", "symptoms", "treatment", "doctor", "health", "medical"
        ]
        
        # If it contains medical terms, treat as medical
        if any(med_word in question_lower for med_word in medical_indicators):
            current_keywords = ["latest", "recent", "new", "current", "2024", "2025", "breakthrough", "study", "research"]
            if any(kw in question_lower for kw in current_keywords):
                return "current_medical"
            return "medical"
        
        # If it's clearly casual, treat as casual
        if any(casual_word in question_lower for casual_word in casual_indicators):
            return "casual"
            
        # If unclear, assume it might be medical (better safe than sorry)
        return "medical"
    
    def create_conversation_prompt(self, user_input, query_type, language="English"):
        """Create appropriate prompts for different conversation types"""
        
        if query_type == "casual":
            prompt = f"""You are GlucoMate, a friendly diabetes care assistant. Someone just said: "{user_input}"

This seems like casual conversation, not a medical question. Respond naturally and conversationally, like a friendly person would. Keep it brief, warm, and natural. You can mention that you're here to help with diabetes questions, but don't make it sound scripted or robotic.

Respond in {language} in a natural, conversational way:"""
        
        else:  # medical queries
            prompt = f"""You are GlucoMate, a warm and caring diabetes companion. A person has asked: "{user_input}"

Please respond in a warm, conversational, and supportive tone that:
1. Provides accurate, evidence-based diabetes information
2. Uses encouraging, friendly language
3. Includes practical tips they can actually use
4. Shows you care about their wellbeing
5. Sounds like a knowledgeable friend, not a medical textbook
6. Keeps medical accuracy while being warm and personal

Respond in {language}:"""
        
        return prompt
        """Search trusted medical sources with better error handling"""
        if not self.search_service:
            return None
            
        try:
            search_query = f"diabetes {query}"
            result = self.search_service.cse().list(q=search_query, cx=self.search_engine_id, num=5).execute()
            
            if 'items' in result:
                return self.process_search_results(result['items'], query)
            return None
        except Exception as e:
            if "quota" in str(e).lower():
                return "I've reached my daily search limit, but let me check my medical knowledge base for you."
            return None
    
    def process_search_results(self, results, original_query):
        """Process search results with warmer tone"""
        try:
            compiled_info = []
            for result in results:
                domain = result['link'].split('/')[2]
                source_name = self.get_source_name(domain)
                compiled_info.append({
                    "title": result['title'],
                    "snippet": result['snippet'],
                    "source": source_name,
                    "url": result['link']
                })
            
            # Create a warm, personalized synthesis prompt
            synthesis_prompt = f"""
            You are GlucoMate, a warm and caring diabetes companion. A person has asked: {original_query}
            
            Based on these trusted medical sources:
            {json.dumps(compiled_info, indent=2)}
            
            Please respond in a warm, conversational, and supportive tone that:
            1. Acknowledges their question with empathy
            2. Provides clear, helpful information from the sources
            3. Uses encouraging language
            4. Includes practical tips they can actually use
            5. Shows you care about their wellbeing
            6. Sounds like a knowledgeable friend, not a medical textbook
            7. Keeps medical accuracy while being warm and personal
            
            Start with a caring acknowledgment, then provide the helpful information in a conversational way.
            """
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "inputText": synthesis_prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 1500,
                        "temperature": 0.3,  # Slightly higher for warmer responses
                        "topP": 0.9
                    }
                }),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            answer = response_body['results'][0]['outputText']
            
            # Add clean source attribution
            sources = f"\n\n💙 I found this information from trusted sources like {', '.join([info['source'] for info in compiled_info[:2]])}."
            
            return answer + sources
            
        except Exception as e:
            return None
    
    def get_source_name(self, domain):
        """Convert domain to friendly source names"""
        source_map = {
            "diabetes.org": "the American Diabetes Association",
            "who.int": "the World Health Organization",
            "cdc.gov": "the CDC",
            "nih.gov": "the National Institutes of Health",
            "pubmed.ncbi.nlm.nih.gov": "medical research studies",
            "mayoclinic.org": "Mayo Clinic",
            "clevelandclinic.org": "Cleveland Clinic",
            "joslin.org": "Joslin Diabetes Center"
        }
        return source_map.get(domain, domain)
    
    def query_medical_knowledge(self, question):
        """Query knowledge base with warmer processing"""
        try:
            response = self.bedrock_agent.retrieve_and_generate(
                input={'text': question},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.knowledge_base_id,
                        'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-text-premier-v1:0'
                    }
                }
            )
            
            raw_answer = response['output']['text']
            
            # Make the knowledge base response warmer
            warm_prompt = f"""
            Take this medical information and rewrite it in a warm, caring, conversational tone:
            
            {raw_answer}
            
            Make it sound like a knowledgeable friend who cares about the person's wellbeing. Keep all the medical accuracy but make it:
            - More personal and encouraging
            - Less clinical and robotic
            - Include practical tips
            - Show empathy and understanding
            - Use "you" and "your" to make it personal
            """
            
            warm_response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "inputText": warm_prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 1200,
                        "temperature": 0.4,
                        "topP": 0.9
                    }
                }),
                contentType='application/json'
            )
            
            warm_body = json.loads(warm_response['body'].read())
            friendly_answer = warm_body['results'][0]['outputText']
            
            return friendly_answer + "\n\n💙 This information comes from medical guidelines and evidence-based research."
            
        except Exception as e:
            if "ThrottlingException" in str(e):
                return "I'm getting a lot of questions right now! Let me try to help you with what I know about diabetes management. What specific aspect would you like to know more about?"
            elif "does not exist" in str(e):
                return "I'm having trouble accessing my medical database right now, but I'd still love to help! Could you ask me something more specific about diabetes care?"
            return None
    
    def translate_to_english(self, text, source_language):
        if source_language == 'en':
            return text
        try:
            response = self.translate_client.translate_text(
                Text=text, SourceLanguageCode=source_language, TargetLanguageCode='en'
            )
            return response['TranslatedText']
        except:
            return text
    
    def translate_response(self, text, target_language):
        if target_language == 'en':
            return text
        try:
            response = self.translate_client.translate_text(
                Text=text, SourceLanguageCode='en', TargetLanguageCode=target_language,
                Settings={'Formality': 'INFORMAL'}  # More conversational
            )
            return response['TranslatedText']
        except:
            return text
    
    def warm_medical_chat(self, user_input, target_language_code):
        """Main chat function with natural conversation and medical responses"""
        
        # Translate to English for processing
        english_input = self.translate_to_english(user_input, target_language_code)
        
        # Check for emergencies first
        safety_check = self.safety.check_emergency_situation(english_input)
        
        if safety_check['is_emergency']:
            emergency_msg = "🚨 I'm really concerned about what you're describing. This sounds like it could be a medical emergency. Please call 911 or go to your nearest emergency room right away. Your safety is the most important thing right now."
            if target_language_code != 'en':
                emergency_msg = self.translate_response(emergency_msg, target_language_code)
            return emergency_msg
        
        # Classify the type of input
        query_type = self.classify_query_type(english_input)
        
        # Get language name for prompt
        language_name = "English"
        for code, (name, lang_code) in self.supported_languages.items():
            if lang_code == target_language_code:
                language_name = name
                break
        
        # Handle casual conversation - use AI but no "thinking" messages
        if query_type == "casual":
            prompt = self.create_conversation_prompt(english_input, query_type, language_name)
            response = self.call_bedrock_model(prompt)
            
            # Translate if needed
            if target_language_code != 'en':
                response = self.translate_response(response, target_language_code)
            
            return response
        
        # For medical queries, show thinking process and try knowledge sources
        response = None
        print("💭 Let me think about this...")
        
        if query_type == "current_medical" and self.search_service:
            print("🔍 Checking the latest medical information for you...")
            web_response = self.search_trusted_medical_sources(english_input)
            if web_response:
                print("✨ Found some current information from trusted sources!")
                response = web_response
        
        if not response:
            print("📚 Looking through my medical knowledge...")
            kb_response = self.query_medical_knowledge(english_input)
            if kb_response:
                print("💡 Found something helpful for you!")
                response = kb_response
        
        # If knowledge base fails, use direct AI response
        if not response:
            print("🧠 Let me help you with what I know...")
            prompt = self.create_conversation_prompt(english_input, query_type, language_name)
            response = self.call_bedrock_model(prompt)
        
        # Add encouragement occasionally
        if any(word in english_input.lower() for word in ['scared', 'worried', 'difficult', 'hard', 'confused']):
            encouragement = "\n\n" + self.encouragement[hash(english_input) % len(self.encouragement)]
            response = response + encouragement
        
        # Translate if needed
        if target_language_code != 'en':
            response = self.translate_response(response, target_language_code)
        
        # Add disclaimer only for medical questions
        disclaimer = "\n\nDisclaimer: This information is educational only. Always consult your healthcare provider for medical decisions."
        if target_language_code != 'en':
            disclaimer = self.translate_response(disclaimer, target_language_code)
        
        # Add high-priority warnings with care
        if safety_check['urgency_level'] == 'HIGH':
            warning = "💛 I'm a bit concerned about what you're describing. It would be really good to check in with your healthcare provider about this soon - they'll be able to give you the best guidance for your specific situation."
            if target_language_code != 'en':
                warning = self.translate_response(warning, target_language_code)
            response = warning + "\n\n" + response
        
        return response + disclaimer

def main():
    print("💙 Hello! I'm GlucoMate, your caring diabetes companion. I'm here to support you with warmth, understanding, and reliable information. Together, we can make managing diabetes feel less overwhelming.")
 
    bot = SmartMedicalSearchGlucoMate()
    
    print(f"\n🌍 I can chat with you in multiple languages!")
    for key, (lang_name, lang_code) in bot.supported_languages.items():
        flag_emoji = {'en': '🇺🇸', 'ar': '🇸🇦', 'fr': '🇫🇷', 'es': '🇪🇸', 'pt': '🇧🇷', 'de': '🇩🇪'}
        print(f"{key}. {flag_emoji.get(lang_code, '')} {lang_name}")
    
    # Get language choice
    while True:
        choice = input("\nWhich language feels most comfortable for you? (1-6): ").strip()
        if choice in bot.supported_languages:
            language_name, language_code = bot.supported_languages[choice]
            break
        else:
            print("Please choose a number between 1-6")
    
    print(f"\n✨ Perfect! Let's chat in {language_name}")
    
    welcome_suggestions = [
        "'What should I know about managing my blood sugar?'",
        "'What foods are good for diabetes?'",
        "'How can exercise help with diabetes?'",
        "'I'm feeling overwhelmed about my diagnosis'",
        "'What should I ask my doctor at my next visit?'"
    ]
    
    print("💙 I'm here to listen and help! You can ask me anything about diabetes.")
    print("🌟 Here are some ways I can support you:")
    for suggestion in welcome_suggestions:
        print(f"   {suggestion}")
    print("\n💬 What's on your mind today? (Type 'bye' when you're ready to go)")
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye', 'stop']:
                farewell = "💙 Take care of yourself! Remember, you're doing great by staying informed about your health. I'm always here when you need support. Wishing you all the best! 🌟"
                if language_code != 'en':
                    farewell = bot.translate_response(farewell, language_code)
                print(f"\n💙 GlucoMate: {farewell}")
                break
            
            if user_input:
                response = bot.warm_medical_chat(user_input, language_code)
                print(f"\n💙 GlucoMate: {response}")
                print("\n" + "─" * 50)
            else:
                print("😊 I'm here whenever you're ready to chat!")
                
    except KeyboardInterrupt:
        print("\n\n💙 GlucoMate: Take care! Remember, you're stronger than you know! 🌟")

if __name__ == "__main__":
    main()
