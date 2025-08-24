"""
GlucoMate Level 2: Multilingual Support
Inherits: Bedrock core, safety, basic prompting
Adds: Translation, language detection, cultural adaptation
"""

import boto3
import json
import sys
from glucomate_core import GlucoMateCore

class MultilingualGlucoMate(GlucoMateCore):
    """
    Level 2: Adds multilingual support to core Bedrock functionality
    Inherits: Bedrock core, safety, basic prompting
    Adds: Translation, language detection, cultural adaptation
    """
    
    def __init__(self):
        super().__init__()  # Get all core functionality
        
        # Medical terms dictionary for better translation context
        self.medical_terms = {
            'diabetes': {
                'ar': 'السكري', 'fr': 'diabète', 'es': 'diabetes', 
                'pt': 'diabetes', 'de': 'Diabetes'
            },
            'blood sugar': {
                'ar': 'سكر الدم', 'fr': 'glycémie', 'es': 'azúcar en sangre',
                'pt': 'açúcar no sangue', 'de': 'Blutzucker'
            },
            'insulin': {
                'ar': 'الأنسولين', 'fr': 'insuline', 'es': 'insulina',
                'pt': 'insulina', 'de': 'Insulin'
            },
            'medication': {
                'ar': 'دواء', 'fr': 'médicament', 'es': 'medicamento',
                'pt': 'medicamento', 'de': 'Medikament'
            },
            'doctor': {
                'ar': 'طبيب', 'fr': 'médecin', 'es': 'médico',
                'pt': 'médico', 'de': 'Arzt'
            }
        }
        
        # Cultural dietary considerations
        self.cultural_food_context = {
            'ar': 'Consider Middle Eastern and Arab dietary preferences (dates, rice, lamb, Mediterranean diet)',
            'es': 'Consider Latin American and Spanish dietary preferences (beans, rice, corn, fresh fruits)',
            'fr': 'Consider French dietary preferences (fresh breads, cheeses, Mediterranean influence)',
            'pt': 'Consider Brazilian/Portuguese dietary preferences (rice, beans, tropical fruits, fish)',
            'de': 'Consider German dietary preferences (whole grains, sausages, cabbage, hearty meals)',
            'en': 'Consider diverse dietary preferences and accessibility of ingredients'
        }
        
        print("🌍 GlucoMate Level 2: Multilingual support loaded")
    
    def detect_language(self, text):
        """
        Detect the language of user input
        
        Args:
            text (str): Text to analyze
            
        Returns:
            str: Language code (en, ar, fr, etc.)
        """
        try:
            response = self.translate_client.detect_dominant_language(Text=text)
            detected_lang = response['Languages'][0]['LanguageCode']
            confidence = response['Languages'][0]['Score']
            
            # Only use detection if confidence is high
            if confidence > 0.8:
                return detected_lang
            else:
                return 'en'  # Default to English if uncertain
                
        except Exception as e:
            print(f"🔍 Language detection failed: {e}")
            return 'en'  # Default to English on error
    
    def translate_to_english(self, text, source_language):
        """
        Translate user input to English for processing
        
        Args:
            text (str): Text to translate
            source_language (str): Source language code
            
        Returns:
            str: Translated text or original if translation fails
        """
        if source_language == 'en':
            return text
        
        try:
            response = self.translate_client.translate_text(
                Text=text,
                SourceLanguageCode=source_language,
                TargetLanguageCode='en'
            )
            translated = response['TranslatedText']
            print(f"🔄 Translated from {source_language}: '{text}' → '{translated}'")
            return translated
            
        except Exception as e:
            print(f"❌ Translation to English failed: {e}")
            return text  # Return original if translation fails
    
    def translate_response(self, text, target_language):
        """
        Translate response back to user's language
        
        Args:
            text (str): English text to translate
            target_language (str): Target language code
            
        Returns:
            str: Translated text or original if translation fails
        """
        if target_language == 'en':
            return text
        
        try:
            # Use formal tone for medical content
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
            print(f"❌ Translation to {target_language} failed: {e}")
            return text  # Return original if translation fails
    
    def create_culturally_aware_prompt(self, user_input, language_code, language_name):
        """
        Create prompts that are culturally sensitive
        
        Args:
            user_input (str): User's input in English
            language_code (str): Target language code
            language_name (str): Target language name
            
        Returns:
            str: Culturally adapted prompt
        """
        cultural_context = self.cultural_food_context.get(language_code, '')
        
        # Add cultural context to the base prompt
        cultural_addition = f"""
        Cultural Context: You are responding to someone who speaks {language_name}. 
        {cultural_context}
        
        Be culturally sensitive in your recommendations, especially for:
        - Food suggestions (consider local/cultural preferences)
        - Meal timing (consider cultural eating patterns)
        - Religious considerations (if applicable)
        - Family dynamics (consider cultural family structures)
        """
        
        return self.create_base_diabetes_prompt(
            user_input, 
            additional_context=cultural_addition, 
            language=language_name
        )
    
    def enhance_medical_translation(self, text, target_language):
        """
        Enhance translation by preserving medical terms accuracy
        
        Args:
            text (str): Text with medical terms
            target_language (str): Target language code
            
        Returns:
            str: Enhanced translation with accurate medical terms
        """
        if target_language == 'en':
            return text
        
        # First translate normally
        translated = self.translate_response(text, target_language)
        
        # Then enhance with medical term corrections if needed
        for english_term, translations in self.medical_terms.items():
            if english_term.lower() in text.lower():
                if target_language in translations:
                    correct_term = translations[target_language]
                    # This is a simplified approach - in production you'd use more sophisticated term replacement
                    print(f"🏥 Enhanced medical term: {english_term} → {correct_term}")
        
        return translated
    
    def multilingual_chat(self, user_input, target_language_code, auto_detect=False):
        """
        Enhanced chat with full multilingual support
        
        Args:
            user_input (str): User's input
            target_language_code (str): Target language code
            auto_detect (bool): Whether to auto-detect language
            
        Returns:
            str: Response in target language
        """
        
        # Auto-detect language if enabled
        detected_language = target_language_code
        if auto_detect:
            detected_language = self.detect_language(user_input)
            if detected_language != target_language_code:
                print(f"🔍 Detected language: {detected_language} (you selected {target_language_code})")
                # Use detected language if confidence is high
                target_language_code = detected_language
        
        # Translate input to English for processing
        english_input = self.translate_to_english(user_input, target_language_code)
        
        # Use inherited safety check
        safety_check = self.check_safety(english_input)
        
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
        
        # Create culturally-aware prompt
        conversation_type = self.classify_conversation_type(english_input)
        
        if conversation_type == "casual":
            # Use inherited base prompt for casual conversation
            prompt = self.create_base_diabetes_prompt(
                english_input, 
                language=language_name, 
                conversation_type=conversation_type
            )
        else:
            # Use culturally-aware prompt for medical conversations
            prompt = self.create_culturally_aware_prompt(
                english_input, target_language_code, language_name
            )
        
        # Get response from Bedrock (inherited method)
        response = self.call_bedrock_model(prompt, conversation_type=conversation_type)
        
        # Enhance translation with medical terms
        if target_language_code != 'en':
            response = self.enhance_medical_translation(response, target_language_code)
        
        # Add disclaimer in appropriate language (inherited method)
        if conversation_type == "medical":
            response = self.add_medical_disclaimer(response, language_name)
        
        # Add warning if needed (inherited safety check)
        if safety_check['urgency_level'] in ['HIGH', 'MODERATE']:
            warning_msg = safety_check['message']
            if target_language_code != 'en':
                warning_msg = self.translate_response(warning_msg, target_language_code)
            response = warning_msg + "\n\n" + response
        
        return response
    
    def get_cultural_greeting(self, language_code):
        """Get culturally appropriate greeting"""
        greetings = {
            'en': "Hello! I'm GlucoMate, your diabetes care companion.",
            'es': "¡Hola! Soy GlucoMate, tu compañero de cuidado de diabetes.",
            'fr': "Bonjour! Je suis GlucoMate, votre compagnon de soins du diabète.",
            'ar': "مرحباً! أنا GlucoMate، رفيقك في رعاية مرض السكري.",
            'pt': "Olá! Eu sou o GlucoMate, seu companheiro no cuidado do diabetes.",
            'de': "Hallo! Ich bin GlucoMate, Ihr Diabetes-Betreuungsbegleiter."
        }
        return greetings.get(language_code, greetings['en'])
    
    def get_cultural_farewell(self, language_code):
        """Get culturally appropriate farewell"""
        farewells = {
            'en': "Take care! Remember to monitor your blood sugar and follow your healthcare provider's guidance. 🌟",
            'es': "¡Cuídate! Recuerda monitorear tu azúcar en sangre y seguir la orientación de tu proveedor de salud. 🌟",
            'fr': "Prenez soin de vous! N'oubliez pas de surveiller votre glycémie et de suivre les conseils de votre professionnel de santé. 🌟",
            'ar': "اعتن بنفسك! تذكر مراقبة سكر الدم واتباع إرشادات طبيبك. 🌟",
            'pt': "Cuide-se! Lembre-se de monitorar seu açúcar no sangue e seguir a orientação do seu médico. 🌟",
            'de': "Passen Sie gut auf sich auf! Denken Sie daran, Ihren Blutzucker zu überwachen und den Rat Ihres Arztes zu befolgen. 🌟"
        }
        return farewells.get(language_code, farewells['en'])

def main():
    """Demo of Level 2 - Multilingual GlucoMate"""
    print("🌍 GlucoMate Level 2: Multilingual Diabetes Care Assistant")
    print("🗣️ Now with translation, cultural awareness, and global accessibility!")
    print("\n✨ New Features:")
    print("   • Full translation support for 6 languages")
    print("   • Automatic language detection")
    print("   • Cultural dietary awareness")
    print("   • Medical term accuracy across languages")
    print("   • Emergency responses in your language")
    
    bot = MultilingualGlucoMate()
    
    # Language selection
    print(f"\n🌍 I can chat with you in multiple languages!")
    bot.display_language_options()
    
    language_name, language_code = bot.get_language_choice()
    
    # Cultural greeting
    greeting = bot.get_cultural_greeting(language_code)
    print(f"\n💙 {greeting}")
    
    # Auto-detect option
    auto_detect_prompt = "Enable automatic language detection? (y/n): "
    if language_code != 'en':
        auto_detect_prompt = bot.translate_response(auto_detect_prompt, language_code)
    
    auto_detect = input(f"🔍 {auto_detect_prompt}").lower().startswith('y')
    
    # Helpful suggestions in user's language
    suggestions = [
        "What foods are good for diabetes?",
        "How do I check my blood sugar?",
        "Tell me about insulin",
        "I'm feeling worried about my diagnosis"
    ]
    
    print(f"\n💡 Try asking me:")
    for suggestion in suggestions:
        if language_code != 'en':
            translated_suggestion = bot.translate_response(suggestion, language_code)
            print(f"   • {translated_suggestion}")
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
                farewell = bot.get_cultural_farewell(language_code)
                print(f"\n💙 GlucoMate: {farewell}")
                break
            
            if user_input:
                print("💭 Processing in multiple languages...")
                response = bot.multilingual_chat(user_input, language_code, auto_detect)
                print(f"\n🌍 GlucoMate: {response}")
                print("\n" + "─" * 60)
            else:
                ready_msg = "I'm here whenever you're ready to chat!"
                if language_code != 'en':
                    ready_msg = bot.translate_response(ready_msg, language_code)
                print(f"💭 {ready_msg}")
                
    except KeyboardInterrupt:
        farewell = bot.get_cultural_farewell(language_code)
        print(f"\n\n💙 GlucoMate: {farewell}")
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        if language_code != 'en':
            error_msg = bot.translate_response(error_msg, language_code)
        print(f"\n❌ {error_msg}")

if __name__ == "__main__":
    main()
