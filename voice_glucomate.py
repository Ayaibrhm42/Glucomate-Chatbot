"""
GlucoMate Voice Interface
A voice-enabled version that can be integrated with speech-to-text and text-to-speech
"""

import boto3
import json
import sys
from health_tracking_glucomate import HealthTrackingGlucoMate

class VoiceGlucoMate(HealthTrackingGlucoMate):
    """
    Voice-enabled GlucoMate with all comprehensive features
    Inherits ALL functionality from Level 6 (complete system)
    Adds: Voice interface considerations and optimizations
    """
    
    def __init__(self, patient_id=None):
        super().__init__(patient_id)  # Get ALL previous functionality
        print("🎙️ GlucoMate Voice Interface: Ready for speech integration")
    
    def process_voice_input(self, transcribed_text, language_code='en', confidence=0.95):
        """
        Process voice input with confidence scoring
        
        Args:
            transcribed_text (str): Text from speech-to-text
            language_code (str): Detected language
            confidence (float): Transcription confidence (0-1)
            
        Returns:
            dict: Response with voice-specific formatting
        """
        
        # Handle low confidence transcriptions
        if confidence < 0.7:
            return {
                "response": "I didn't quite catch that. Could you please repeat your question?",
                "voice_optimized": True,
                "ask_for_repeat": True
            }
        
        # Clean up common voice transcription issues
        cleaned_text = self.clean_voice_input(transcribed_text)
        
        # Use comprehensive chat (gets ALL features from all levels)
        response = self.comprehensive_chat(cleaned_text, language_code)
        
        # Optimize response for voice output
        voice_response = self.optimize_for_voice_output(response)
        
        return {
            "response": voice_response,
            "voice_optimized": True,
            "original_text": transcribed_text,
            "cleaned_text": cleaned_text
        }
    
    def clean_voice_input(self, text):
        """Clean common voice transcription errors"""
        
        # Common diabetes voice transcription fixes
        corrections = {
            'sugar level': 'blood sugar level',
            'glucose level': 'blood glucose level', 
            'diabetic': 'diabetes',
            'insulin shot': 'insulin injection',
            'blood test': 'glucose test',
            'sugar reading': 'glucose reading',
            # Add more as needed
        }
        
        cleaned = text
        for error, correction in corrections.items():
            cleaned = cleaned.replace(error, correction)
        
        return cleaned
    
    def optimize_for_voice_output(self, text_response):
        """Optimize text response for speech synthesis"""
        
        # Remove or replace elements that don't speak well
        voice_optimized = text_response
        
        # Replace symbols and emojis with spoken equivalents
        replacements = {
            '📊': 'Based on your data, ',
            '🎯': 'Great news: ',
            '⚠️': 'Important: ',
            '✅': 'Good: ',
            '❌': 'Note: ',
            '💙': '',
            '🌟': '',
            '📋': 'Please remember: ',
            '🔍': '',
            '💡': 'Here\'s a tip: ',
            # Remove markdown formatting
            '**': '',
            '*': '',
            '#': '',
            '---': '. ',
            '###': '',
        }
        
        for symbol, replacement in replacements.items():
            voice_optimized = voice_optimized.replace(symbol, replacement)
        
        # Break up long sentences for better speech flow
        voice_optimized = self.break_long_sentences(voice_optimized)
        
        # Add natural pauses
        voice_optimized = voice_optimized.replace('. ', '. <break time="0.5s"/> ')
        voice_optimized = voice_optimized.replace('! ', '! <break time="0.3s"/> ')
        voice_optimized = voice_optimized.replace('? ', '? <break time="0.3s"/> ')
        
        return voice_optimized
    
    def break_long_sentences(self, text):
        """Break up sentences that are too long for comfortable speech"""
        sentences = text.split('. ')
        improved_sentences = []
        
        for sentence in sentences:
            if len(sentence) > 100:  # Long sentence
                # Try to break at natural points
                if ', and ' in sentence:
                    parts = sentence.split(', and ')
                    improved_sentences.append(parts[0] + '.')
                    improved_sentences.append('And ' + ', and '.join(parts[1:]))
                elif ', but ' in sentence:
                    parts = sentence.split(', but ')
                    improved_sentences.append(parts[0] + '.')
                    improved_sentences.append('But ' + ', but '.join(parts[1:]))
                else:
                    improved_sentences.append(sentence)
            else:
                improved_sentences.append(sentence)
        
        return '. '.join(improved_sentences)
    
    def get_voice_commands(self):
        """Get list of supported voice commands"""
        return {
            "check_in": ["weekly check in", "do my check in", "start check in"],
            "progress": ["how am I doing", "show my progress", "progress report"],
            "meal_plan": ["create meal plan", "make meal plan", "food suggestions"],
            "glucose": ["blood sugar", "glucose level", "sugar reading"],
            "medication": ["medication reminder", "my medications", "pill reminder"],
            "help": ["help me", "what can you do", "show options"]
        }

def main():
    """Demo of Voice Interface GlucoMate"""
    print("🎙️ GlucoMate Voice Interface Demo")
    print("🗣️ Optimized for speech-to-text and text-to-speech integration")
    print("\n✨ Voice Features:")
    print("   • Confidence-based input processing")
    print("   • Voice transcription error correction")
    print("   • Speech-optimized output formatting")
    print("   • All comprehensive GlucoMate features")
    
    # Use demo patient from health tracking
    from health_tracking_glucomate import setup_demo_tracking_patient
    demo_patient_id = setup_demo_tracking_patient()
    
    voice_bot = VoiceGlucoMate(patient_id=demo_patient_id)
    
    # Show voice commands
    commands = voice_bot.get_voice_commands()
    print(f"\n🎤 Supported Voice Commands:")
    for category, command_list in commands.items():
        print(f"   • {category.replace('_', ' ').title()}: {', '.join(command_list[:2])}")
    
    print(f"\n💬 Voice Interface Ready! (Type to simulate voice input)")
    print("Note: In production, this would integrate with speech-to-text services")
    
    try:
        while True:
            # Simulate voice input
            user_input = input(f"\n🎙️ Voice Input: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye', 'stop']:
                farewell = "Thanks for using GlucoMate Voice! Take care of your diabetes, and remember I'm always here to help. Goodbye!"
                print(f"\n🎙️ GlucoMate: {farewell}")
                break
            
            if user_input:
                # Simulate voice processing
                confidence = 0.95  # Simulated high confidence
                voice_result = voice_bot.process_voice_input(user_input, 'en', confidence)
                
                print(f"\n🎙️ GlucoMate (Voice): {voice_result['response']}")
                
                if voice_result.get('ask_for_repeat'):
                    print("   (Voice system would ask user to repeat)")
                    
                print("\n" + "─" * 60)
            else:
                print("🎙️ Voice interface listening...")
                
    except KeyboardInterrupt:
        print(f"\n\n🎙️ GlucoMate Voice: Goodbye! Stay healthy! 🌟")

if __name__ == "__main__":
    main()
