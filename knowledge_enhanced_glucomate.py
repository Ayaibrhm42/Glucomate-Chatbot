import boto3
import json
import sys
from medical_safety import MedicalSafetyGuardrails

class KnowledgeEnhancedGlucoMate:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        self.translate_client = boto3.client('translate', region_name='us-east-1')
        self.safety = MedicalSafetyGuardrails()
        self.model_id = "amazon.titan-text-premier-v1:0"
        
        # Your actual Knowledge Base ID
        self.knowledge_base_id = "GXJOYBIHCU"
        
        # Supported languages
        self.supported_languages = {
            '1': ('English', 'en'),
            '2': ('Arabic', 'ar'), 
            '3': ('French', 'fr'),
            '4': ('Spanish', 'es'),
            '5': ('Portuguese', 'pt'),
            '6': ('German', 'de')
        }
    
    def query_medical_knowledge(self, question):
        """Query the diabetes knowledge base for authoritative information"""
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
            
            # Extract response and sources
            answer = response['output']['text']
            sources = response.get('citations', [])
            
            # Add source information
            if sources:
                source_info = "\n\n📚 **Sources**: Information from authoritative diabetes care guidelines and medical literature."
                answer += source_info
            
            return answer
            
        except Exception as e:
            print(f"Knowledge base query failed: {e}")
            return None
    
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
            return text
    
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
                    'Formality': 'FORMAL'
                }
            )
            return response['TranslatedText']
        except Exception as e:
            print(f"Translation failed: {e}")
            return text
    
    def enhanced_chat(self, user_input, target_language_code):
        """Enhanced chat with knowledge base integration"""
        
        # Translate input to English for processing
        english_input = self.translate_to_english(user_input, target_language_code)
        
        # Check for emergency situations first
        safety_check = self.safety.check_emergency_situation(english_input)
        
        if safety_check['is_emergency']:
            emergency_msg = safety_check['message']
            if target_language_code != 'en':
                emergency_msg = self.translate_response(emergency_msg, target_language_code)
            return emergency_msg
        
        # Query knowledge base for medical information
        print("🔍 Searching medical knowledge base...")
        kb_response = self.query_medical_knowledge(english_input)
        
        if kb_response:
            # Use knowledge base response
            response = kb_response
            print("✅ Response from medical knowledge base")
        else:
            # Fallback to regular AI response
            print("⚠️ Using fallback AI response")
            response = "I apologize, but I couldn't retrieve specific medical information from our knowledge base. Please consult your healthcare provider for accurate medical guidance."
        
        # Translate response if needed
        if target_language_code != 'en':
            response = self.translate_response(response, target_language_code)
        
        # Add medical disclaimer
        disclaimer = "\n\n📋 **Medical Disclaimer**: This information is for educational purposes only. Always consult your healthcare provider for medical decisions."
        if target_language_code != 'en':
            disclaimer = self.translate_response(disclaimer, target_language_code)
        
        # Add warning if needed
        if safety_check['urgency_level'] == 'HIGH':
            warning_msg = safety_check['message']
            if target_language_code != 'en':
                warning_msg = self.translate_response(warning_msg, target_language_code)
            response = warning_msg + "\n\n" + response
        
        return response + disclaimer

def main():
    print("🧠 GlucoMate with Medical Knowledge Base")
    print("🏥 Enhanced with authoritative diabetes care information")
    print("🌍 Multilingual support available")
    
    bot = KnowledgeEnhancedGlucoMate()
    
    print("\nChoose your language:")
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
    print("🩺 Ask me anything about diabetes management!")
    print("💡 Try: 'What are normal blood sugar levels?' or 'What should I eat?'")
    print("Type 'quit' to exit\n")
    
    try:
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'stop']:
                farewell = "Take care! Remember to follow your healthcare provider's advice. 👋"
                if language_code != 'en':
                    farewell = bot.translate_response(farewell, language_code)
                print(f"GlucoMate: {farewell}")
                break
            
            if user_input:
                response = bot.enhanced_chat(user_input, language_code)
                print(f"\n🩺 GlucoMate: {response}\n")
                print("-" * 60)
            else:
                print("Please enter a question or type 'quit' to exit.")
                
    except KeyboardInterrupt:
        print("\n\n🩺 GlucoMate: Goodbye! Take care! 👋")

if __name__ == "__main__":
    main()
