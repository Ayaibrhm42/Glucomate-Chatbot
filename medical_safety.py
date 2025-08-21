class MedicalSafetyGuardrails:
    def __init__(self):
        self.emergency_keywords = [
            'severe hypoglycemia', 'blood sugar below 50', 'unconscious',
            'diabetic ketoacidosis', 'dka', 'blood sugar over 400',
            'vomiting repeatedly', 'difficulty breathing', 'chest pain',
            'severe dehydration', 'can\'t keep fluids down'
        ]
        
        self.warning_keywords = [
            'blood sugar over 300', 'ketones in urine', 'blurred vision',
            'frequent urination', 'extreme thirst', 'unexplained weight loss'
        ]
    
    def check_emergency_situation(self, user_input):
        user_text = user_input.lower()
        
        for keyword in self.emergency_keywords:
            if keyword in user_text:
                return {
                    'is_emergency': True,
                    'urgency_level': 'EMERGENCY',
                    'message': '🚨 MEDICAL EMERGENCY: Please call emergency services (911) immediately or go to the nearest emergency room!'
                }
        
        for keyword in self.warning_keywords:
            if keyword in user_text:
                return {
                    'is_emergency': False,
                    'urgency_level': 'HIGH',
                    'message': '⚠️ Warning: Please contact your healthcare provider as soon as possible about these symptoms.'
                }
        
        return {'is_emergency': False, 'urgency_level': 'NORMAL', 'message': ''}
    
    def add_medical_disclaimer(self, response):
        disclaimer = "\n\n📋 **Medical Disclaimer**: This information is for educational purposes only and is not a substitute for professional medical advice. Always consult your healthcare provider for medical decisions."
        return response + disclaimer

if __name__ == "__main__":
    safety = MedicalSafetyGuardrails()
    test_input = "My blood sugar is 450 and I'm vomiting"
    result = safety.check_emergency_situation(test_input)
    print(f"Emergency check: {result}")
