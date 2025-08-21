import boto3
import json
import sys
from medical_safety import MedicalSafetyGuardrails

class MultilingualGlucoMate:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.translate_client = boto3.client('translate', region_name='us-east-1')
        self.safety = MedicalSafetyGuardrails()
        self.model_id = "amazon.titan-text-premier-v1:0"
        
        # Supported languages for GlucoMate
        self.supported_languages = {
            '1': ('English', 'en'),
            '2': ('Arabic', 'ar'), 
            '3': ('French', 'fr'),
            '4': ('Spanish', 'es'),
            '5': ('Portuguese', 'pt'),
            '6': ('German', 'de')
        }
        
        # Medical terms dictionary for better translation
        self.medical_terms = {
            'diabetes': {'ar': 'السكري', 'fr': 'diabète', 'es': 'diabetes'},
            'blood sugar': {'ar': 'سكر الدم', 'fr': 'glycémie', 'es': 'azúcar en sangre'},
            'insulin': {'ar': 'الأنسولين', 'fr': 'insuline', 'es': 'insulina'},
            'medication': {'ar': 'دواء', 'fr': 'médicament', 'es': 'medicamento'}
        }
    
    def call_bedrock_model(self, prompt):
        try:
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 2048,
                    "temperature": 0.1,
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
            return f"Error calling Bedrock: {str(e)}"
    
    def detect_language(self, text):
        """Detect the language of user input"""
        try:
            response = self.translate_client.detect_dominant_language(Text=text)
            detected_lang = response['Languages'][0]['LanguageCode']
            confidence = response['Languages'][0]['Score']
            
            # Only use detection if confidence is high
            if confidence > 0.8:
                return detected_lang
            else:
                return 'en'  # Default to English
        except Exception as e:
            print(f"Language detection failed: {e}")
            return 'en'  # Default to English
    
    def translate_to_english(self, text, source_language):
        """Translate user input to English for processing"""
        if source_language == 'en':
            return text
        
        try:
            response = self.translate_client.translate_text(
                Text=text,
                SourceLanguageCode=source_language,
                TargetLanguageCode='en'
            )
            return response['TranslatedText']
        except Exception as e:
            print(f"Translation to English failed: {e}")
            return text  # Return original if translation fails
    
    def translate_response(self, text, target_language):
        """Translate response back to user's language"""
        if target_language == 'en':
            return text
        
        try:
            response = self.translate_client.translate_text(
                Text=text,
                SourceLanguageCode='en',
                TargetLanguageCode=target_language,
                Settings={
                    'Formality': 'FORMAL'  # Use formal tone for medical content
                }
            )
            return response['TranslatedText']
        except Exception as e:
            print(f"Translation failed: {e}")
            return text  # Return original if translation fails
    
    def create_diabetes_prompt(self, user_question, language="English"):
        """Create specialized diabetes prompt"""
        prompt = f"""You are GlucoMate, an AI assistant specialized in diabetes care and education. You provide accurate, evidence-based information about diabetes management.

User Question: {user_question}
Response Language: {language}

Guidelines for your response:
1. Provide accurate, evidence-based diabetes information
2. Be empathetic and supportive  
3. Use simple, clear language appropriate for patients
4. Include practical actionable advice when appropriate
5. Always emphasize the importance of healthcare provider consultation
6. If discussing medications, mention the need for doctor supervision
7. For nutrition advice, provide general guidelines but recommend personalized plans
8. Be culturally sensitive for {language} speakers
9. Keep responses concise but comprehensive

Important: Respond in {language} if possible, or indicate if you need to respond in English."""
        
        return prompt
    
    def chat(self, user_input, target_language_code, auto_detect=False):
        """Main chat function with multilingual support"""
        
        # Auto-detect language if enabled
        if auto_detect:
            detected_lang = self.detect_language(user_input)
            print(f"🔍 Detected language: {detected_lang}")
        
        # Check for emergency situations (translate to English first if needed)
        english_input = self.translate_to_english(user_input, target_language_code)
        safety_check = self.safety.check_emergency_situation(english_input)
        
        if safety_check['is_emergency']:
            emergency_msg = safety_check['message']
            # Translate emergency message to user's language
            if target_language_code != 'en':
                emergency_msg = self.translate_response(emergency_msg, target_language_code)
            return emergency_msg
        
        # Get language name for prompt
        language_name = "English"
        for code, (name, lang_code) in self.supported_languages.items():
            if lang_code == target_language_code:
                language_name = name
                break
        
        # Generate diabetes-specific prompt
        prompt = self.create_diabetes_prompt(english_input, language_name)
        
        # Get response from Bedrock
        response = self.call_bedrock_model(prompt)
        
        # Translate response if needed
        if target_language_code != 'en':
            response = self.translate_response(response, target_language_code)
        
        # Add safety disclaimer (translated)
        disclaimer = "📋 Medical Disclaimer: This information is for educational purposes only and is not a substitute for professional medical advice. Always consult your healthcare provider for medical decisions."
        if target_language_code != 'en':
            disclaimer = self.translate_response(disclaimer, target_language_code)
        
        safe_response = response + "\n\n" + disclaimer
        
        # Add warning if needed
        if safety_check['urgency_level'] == 'HIGH':
            warning_msg = safety_check['message']
            if target_language_code != 'en':
                warning_msg = self.translate_response(warning_msg, target_language_code)
            safe_response = warning_msg + "\n\n" + safe_response
        
        return safe_response

def main():
    bot = MultilingualGlucoMate()
    
    print("🩺 Welcome to GlucoMate - Multilingual Diabetes Care Assistant")
    print("🌍 مرحباً بكم في GlucoMate - Bienvenue à GlucoMate - Bienvenido a GlucoMate")
    print("\nChoose your preferred language:")
    
    for key, (lang_name, lang_code) in bot.supported_languages.items():
        flag_emoji = {'en': '🇺🇸', 'ar': '🇸🇦', 'fr': '🇫🇷', 'es': '🇪🇸', 'pt': '🇧🇷', 'de': '🇩🇪'}
        print(f"{key}. {flag_emoji.get(lang_code, '🌍')} {lang_name}")
    
    # Get language choice
    while True:
        choice = input("\nEnter your choice (1-6): ").strip()
        if choice in bot.supported_languages:
            language_name, language_code = bot.supported_languages[choice]
            break
        else:
            print("Invalid choice. Please enter 1-6.")
    
    print(f"\n✅ Selected: {language_name}")
    
    # Translate welcome message
    welcome_msg = "Ask me anything about diabetes management, nutrition, medications, or symptoms! Type 'quit' to exit."
    if language_code != 'en':
        welcome_msg = bot.translate_response(welcome_msg, language_code)
    
    print(f"🤖 {welcome_msg}\n")
    
    # Auto-detect option
    auto_detect = input("🔍 Enable automatic language detection? (y/n): ").lower().startswith('y')
    print()
    
    try:
        while True:
            try:
                user_input = input("You: ").strip()
                
                # Multiple exit conditions
                exit_words = ['quit', 'exit', 'bye', 'stop', 'end', 'q']
                # Add translated exit words
                if language_code == 'ar':
                    exit_words.extend(['خروج', 'إنهاء', 'توقف'])
                elif language_code == 'fr':
                    exit_words.extend(['quitter', 'sortir', 'arrêter'])
                elif language_code == 'es':
                    exit_words.extend(['salir', 'terminar', 'parar'])
                
                if user_input.lower() in exit_words:
                    farewell = "Take care! Remember to monitor your blood sugar regularly and follow your healthcare provider's advice. 👋"
                    if language_code != 'en':
                        farewell = bot.translate_response(farewell, language_code)
                    print(f"GlucoMate: {farewell}")
                    sys.exit(0)
                
                if user_input:
                    response = bot.chat(user_input, language_code, auto_detect)
                    print(f"\n🩺 GlucoMate: {response}\n")
                    print("-" * 60)
                else:
                    prompt_msg = "Please enter a question or type 'quit' to exit."
                    if language_code != 'en':
                        prompt_msg = bot.translate_response(prompt_msg, language_code)
                    print(prompt_msg)
                    
            except KeyboardInterrupt:
                farewell = "Goodbye! Take care of your health! 👋"
                if language_code != 'en':
                    farewell = bot.translate_response(farewell, language_code)
                print(f"\n\n🩺 GlucoMate: {farewell}")
                sys.exit(0)
            except EOFError:
                print("\n\n🩺 GlucoMate: Session ended. Take care! 👋")
                sys.exit(0)
                
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
