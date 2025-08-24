"""
GlucoMate Core - Level 1: Base Bedrock Foundation
Provides consistent Bedrock integration and core functionality for all GlucoMate variants
"""

import boto3
import json
import sys
import os
from medical_safety import MedicalSafetyGuardrails

class GlucoMateCore:
    """
    Base class for all GlucoMate variants.
    Ensures consistent Bedrock usage and core functionality across all files.
    """
    
    def __init__(self):
        # Standardized AWS clients
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        self.translate_client = boto3.client('translate', region_name='us-east-1')
        
        # Consistent model configuration across ALL GlucoMate variants
        self.model_id = "amazon.titan-text-premier-v1:0"
        self.default_temperature = 0.3  # Medical accuracy focused
        self.max_tokens = 2048
        self.top_p = 0.9
        
        # Safety guardrails (consistent across all implementations)
        self.safety = MedicalSafetyGuardrails()
        
        # Standardized language support
        self.supported_languages = {
            '1': ('English', 'en'),
            '2': ('Arabic', 'ar'), 
            '3': ('French', 'fr'),
            '4': ('Spanish', 'es'),
            '5': ('Portuguese', 'pt'),
            '6': ('German', 'de')
        }
        
        # Consistent encouragement phrases
        self.encouragement = [
            "You're taking a positive step by learning about your health.",
            "It's wonderful that you're being proactive about your diabetes care.",
            "Taking control of your diabetes is empowering - you're on the right track.",
            "Every small step towards better health matters.",
            "You're not alone in this journey - many people successfully manage diabetes."
        ]
        
        # Core conversation starters for consistency
        self.conversation_starters = [
            "I understand you're looking for information about",
            "Let me help you with that question about",
            "That's a great question about",
            "I'm here to help you understand",
            "Let me share what I know about"
        ]
    
    def call_bedrock_model(self, prompt, temperature=None, max_tokens=None, conversation_type="medical"):
        """
        Standardized Bedrock model calling with consistent error handling
        
        Args:
            prompt (str): The prompt to send to Bedrock
            temperature (float): Override default temperature
            max_tokens (int): Override default max tokens  
            conversation_type (str): 'medical', 'casual', 'emergency'
        
        Returns:
            str: The response from Bedrock or an error message
        """
        # Adjust temperature based on conversation type for optimal responses
        if temperature is None:
            if conversation_type == "medical":
                temperature = 0.1  # More precise for medical accuracy
            elif conversation_type == "casual":
                temperature = 0.4  # More conversational and natural
            elif conversation_type == "emergency":
                temperature = 0.05  # Maximum precision for safety
            else:
                temperature = self.default_temperature
        
        if max_tokens is None:
            max_tokens = self.max_tokens
            
        try:
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature,
                    "topP": self.top_p,
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
            return self._handle_bedrock_error(e)
    
    def _handle_bedrock_error(self, error):
        """Standardized error handling for Bedrock calls"""
        error_str = str(error)
        
        if "ThrottlingException" in error_str:
            return "I'm getting a lot of questions right now! Please try again in a moment. I'm here whenever you're ready."
        elif "ValidationException" in error_str:
            return "I'm having trouble processing that request. Could you try rephrasing your question? I want to make sure I give you the best answer possible."
        elif "AccessDeniedException" in error_str:
            return "I'm having authentication issues with my AI system. Please check the system configuration or try again in a few minutes."
        elif "ServiceQuotaExceededException" in error_str:
            return "I've reached my usage limit for now. Please try again in a few minutes, and I'll be ready to help!"
        elif "InternalServerException" in error_str:
            return "I'm experiencing some internal issues. Please try again in a moment - I should be back to normal shortly."
        else:
            return f"I'm experiencing technical difficulties right now. Please try again in a moment. If the problem persists, the technical details are: {error_str[:100]}"
    
    def check_safety(self, user_input):
        """Standardized safety checking across all implementations"""
        return self.safety.check_emergency_situation(user_input)
    
    def create_base_diabetes_prompt(self, user_input, additional_context="", language="English", conversation_type="medical"):
        """
        Base diabetes prompt that all implementations can extend
        
        Args:
            user_input (str): User's question/input
            additional_context (str): Any additional context (profile, history, etc.)
            language (str): Target language for response
            conversation_type (str): Type of conversation for tone adjustment
            
        Returns:
            str: Complete prompt ready for Bedrock
        """
        
        if conversation_type == "casual":
            base_prompt = f"""You are GlucoMate, a friendly and caring diabetes companion. Someone said: "{user_input}"

This seems like casual conversation. Respond naturally and warmly, like a knowledgeable friend would. Keep it brief but caring. You can mention that you're here to help with diabetes questions if appropriate, but don't make it sound scripted.

{additional_context}

Respond in {language} in a natural, conversational way:"""
        
        elif conversation_type == "emergency":
            base_prompt = f"""You are GlucoMate, a medical AI assistant. This appears to be a medical emergency situation: "{user_input}"

Provide immediate, clear guidance prioritizing the person's safety. Be direct and authoritative. Guide them to emergency services if needed.

{additional_context}

Respond in {language} with clear, emergency-appropriate guidance:"""
        
        else:  # medical or other types
            base_prompt = f"""You are GlucoMate, an AI assistant specialized in diabetes care and education. You provide accurate, evidence-based information about diabetes management with warmth and empathy.

User Input: {user_input}
Response Language: {language}

{additional_context}

Guidelines for your response:
1. Provide accurate, evidence-based diabetes information
2. Be empathetic, supportive, and encouraging
3. Use simple, clear language appropriate for patients
4. Include practical, actionable advice when appropriate
5. Always emphasize the importance of healthcare provider consultation
6. If discussing medications, mention the need for doctor supervision
7. For nutrition advice, provide general guidelines but recommend personalized plans
8. Be culturally sensitive for {language} speakers
9. Keep responses concise but comprehensive
10. Sound like a knowledgeable, caring friend rather than a medical textbook

Respond in {language}:"""
        
        return base_prompt
    
    def add_medical_disclaimer(self, response, language="English"):
        """Standardized medical disclaimer in multiple languages"""
        return self.safety.add_medical_disclaimer(response, language)
    
    def classify_conversation_type(self, user_input):
        """
        Classify conversation type for appropriate response handling
        
        Returns:
            str: 'emergency', 'casual', 'medical'
        """
        user_input_lower = user_input.lower()
        
        # Emergency indicators
        emergency_keywords = [
            'emergency', 'urgent', 'help', '911', 'hospital', 'dying', 'emergency room',
            'ambulance', 'call doctor', 'severe', 'can\'t breathe', 'chest pain',
            'unconscious', 'passed out', 'blood sugar 400', 'dka', 'ketoacidosis'
        ]
        if any(keyword in user_input_lower for keyword in emergency_keywords):
            return "emergency"
        
        # Casual conversation indicators  
        casual_keywords = [
            'hi', 'hello', 'hey', 'how are you', 'what\'s up', 'thanks', 'thank you',
            'good morning', 'good afternoon', 'good evening', 'bye', 'goodbye',
            'comment ça va', 'ça va', 'كيف حالك', '¿cómo estás', 'hola', 'bonjour',
            'guten tag', 'bom dia', 'marhaba'
        ]
        if any(keyword in user_input_lower for keyword in casual_keywords):
            return "casual"
        
        # Medical conversation (default)
        return "medical"
    
    def generate_core_response(self, user_input, language="English"):
        """
        Core response generation that all implementations can use/extend
        
        Args:
            user_input (str): User's input
            language (str): Target language
            
        Returns:
            str: Complete response with safety checks and disclaimers
        """
        # Safety check first - this is critical
        safety_check = self.check_safety(user_input)
        
        if safety_check['is_emergency']:
            return safety_check['message']
        
        # Classify conversation type
        conversation_type = self.classify_conversation_type(user_input)
        
        # Create appropriate prompt
        prompt = self.create_base_diabetes_prompt(
            user_input, 
            language=language, 
            conversation_type=conversation_type
        )
        
        # Get response from Bedrock
        response = self.call_bedrock_model(prompt, conversation_type=conversation_type)
        
        # Add disclaimer for medical conversations
        if conversation_type == "medical":
            response = self.add_medical_disclaimer(response, language)
        
        # Add warning if needed
        if safety_check['urgency_level'] == 'HIGH':
            response = safety_check['message'] + "\n\n" + response
        elif safety_check['urgency_level'] == 'MODERATE':
            response = safety_check['message'] + "\n\n" + response
        
        return response
    
    def display_language_options(self):
        """Standardized language selection display"""
        print("\n🌍 Choose your preferred language:")
        flag_emojis = {
            'en': '🇺🇸', 'ar': '🇸🇦', 'fr': '🇫🇷', 
            'es': '🇪🇸', 'pt': '🇧🇷', 'de': '🇩🇪'
        }
        
        for key, (lang_name, lang_code) in self.supported_languages.items():
            emoji = flag_emojis.get(lang_code, '🌍')
            print(f"   {key}. {emoji} {lang_name}")
    
    def get_language_choice(self):
        """Standardized language selection logic"""
        self.display_language_options()
        
        while True:
            choice = input("\nEnter your choice (1-6): ").strip()
            if choice in self.supported_languages:
                language_name, language_code = self.supported_languages[choice]
                print(f"\n✅ Selected: {language_name}")
                return language_name, language_code
            else:
                print("❌ Invalid choice. Please enter a number between 1-6.")
    
    def handle_exit_commands(self, user_input, language_code='en'):
        """Check for exit commands in multiple languages"""
        exit_commands = {
            'en': ['quit', 'exit', 'bye', 'goodbye', 'stop', 'end'],
            'es': ['salir', 'adiós', 'terminar', 'parar'],
            'fr': ['quitter', 'au revoir', 'arrêter', 'sortir'],
            'ar': ['خروج', 'وداعا', 'إنهاء', 'توقف'],
            'pt': ['sair', 'tchau', 'parar', 'terminar'],
            'de': ['beenden', 'auf wiedersehen', 'tschüss', 'stopp']
        }
        
        user_lower = user_input.lower().strip()
        
        # Check all language exit commands
        for lang, commands in exit_commands.items():
            if user_lower in commands:
                return True
        
        return False
    
    def get_farewell_message(self, language_code='en'):
        """Get farewell message in appropriate language"""
        farewells = {
            'en': "Take care! Remember to monitor your blood sugar regularly and follow your healthcare provider's advice. You're doing great managing your diabetes! 👋",
            'es': "¡Cuídate! Recuerda monitorear tu azúcar en sangre regularmente y seguir los consejos de tu proveedor de salud. ¡Lo estás haciendo muy bien manejando tu diabetes! 👋",
            'fr': "Prenez soin de vous! N'oubliez pas de surveiller régulièrement votre glycémie et de suivre les conseils de votre professionnel de santé. Vous gérez très bien votre diabète! 👋",
            'ar': "اعتن بنفسك! تذكر مراقبة سكر الدم بانتظام واتباع نصائح طبيبك. أنت تدير مرض السكري بشكل رائع! 👋",
            'pt': "Cuide-se! Lembre-se de monitorar seu açúcar no sangue regularmente e seguir os conselhos do seu médico. Você está indo muito bem no controle do diabetes! 👋",
            'de': "Passen Sie auf sich auf! Denken Sie daran, Ihren Blutzucker regelmäßig zu überwachen und den Rat Ihres Arztes zu befolgen. Sie managen Ihren Diabetes großartig! 👋"
        }
        
        return farewells.get(language_code, farewells['en'])

# Level 1 Implementation: Basic GlucoMate with standardized core
class GlucoMateBot(GlucoMateCore):
    """
    Level 1: Basic GlucoMate with standardized Bedrock core
    Features: Core Bedrock integration, safety checks, basic diabetes prompting
    """
    
    def __init__(self):
        super().__init__()  # Get all core functionality
        print("🩺 GlucoMate Level 1: Core Bedrock functionality loaded")
    
    def chat(self, user_input, language="English"):
        """Simple chat using core functionality"""
        return self.generate_core_response(user_input, language)

def main():
    """Demo of Level 1 - Core GlucoMate functionality"""
    print("🩺 GlucoMate Core - Level 1: Standardized Bedrock Implementation")
    print("🏥 Your AI diabetes care companion with consistent, safe responses")
    print("✨ This is the foundation that all other GlucoMate versions build upon")
    print("\n💡 Features:")
    print("   • Standardized AWS Bedrock integration")
    print("   • Comprehensive safety guardrails")
    print("   • Evidence-based diabetes information")
    print("   • Warm, supportive conversation style")
    
    bot = GlucoMateBot()
    
    print(f"\n💬 Ask me anything about diabetes management!")
    print("🌟 Try: 'What is diabetes?' or 'How do I check my blood sugar?'")
    print("Type 'quit' to exit\n")
    
    try:
        while True:
            user_input = input("😊 You: ").strip()
            
            if bot.handle_exit_commands(user_input):
                print(f"\n💙 GlucoMate: {bot.get_farewell_message()}")
                break
            
            if user_input:
                print("\n💭 Thinking...")
                response = bot.chat(user_input)
                print(f"\n🩺 GlucoMate: {response}")
                print("\n" + "─" * 60)
            else:
                print("💭 I'm here whenever you're ready to chat!")
                
    except KeyboardInterrupt:
        print(f"\n\n💙 GlucoMate: {bot.get_farewell_message()}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        print("Please restart the application.")

if __name__ == "__main__":
    main()
