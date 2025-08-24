"""
Medical Safety Guardrails for GlucoMate
Handles emergency detection, warning signs, and medical disclaimers
"""

class MedicalSafetyGuardrails:
    def __init__(self):
        # Critical emergency keywords requiring immediate medical attention
        self.emergency_keywords = [
            'severe hypoglycemia', 'blood sugar below 50', 'blood sugar under 50',
            'unconscious', 'passed out', 'unresponsive', 'not responding',
            'diabetic ketoacidosis', 'dka', 'blood sugar over 400', 'blood sugar above 400',
            'vomiting repeatedly', 'can\'t stop vomiting', 'throwing up repeatedly',
            'difficulty breathing', 'trouble breathing', 'can\'t breathe',
            'chest pain', 'heart pain', 'severe chest pain',
            'severe dehydration', 'extremely dehydrated',
            'can\'t keep fluids down', 'cannot keep water down',
            'ketones high', 'high ketones', 'ketones in blood',
            'fruity breath', 'acetone breath',
            'severe abdominal pain', 'severe stomach pain',
            'rapid heart rate', 'heart racing dangerously',
            'confusion severe', 'extremely confused', 'altered consciousness',
            'seizure', 'convulsions', 'fitting'
        ]
        
        # Warning keywords requiring prompt medical consultation
        self.warning_keywords = [
            'blood sugar over 300', 'blood sugar above 300', 'glucose over 300',
            'blood sugar over 250', 'blood sugar above 250',
            'ketones in urine', 'ketones positive', 'ketones detected',
            'blurred vision', 'vision problems', 'can\'t see clearly',
            'frequent urination', 'urinating constantly', 'peeing all the time',
            'extreme thirst', 'extremely thirsty', 'can\'t quench thirst',
            'unexplained weight loss', 'losing weight rapidly', 'weight dropping',
            'persistent nausea', 'feeling sick constantly', 'nauseous all day',
            'fatigue extreme', 'extremely tired', 'exhausted constantly',
            'wounds not healing', 'cuts not healing', 'slow healing',
            'numbness in feet', 'tingling in hands', 'nerve pain',
            'swollen feet', 'swelling in legs', 'edema',
            'blood sugar won\'t come down', 'glucose stuck high',
            'medication not working', 'insulin not effective'
        ]
        
        # Moderate concern keywords requiring monitoring
        self.moderate_concern_keywords = [
            'blood sugar over 200', 'glucose above 200',
            'blood sugar below 70', 'glucose under 70',
            'feeling shaky', 'trembling', 'jittery',
            'sweating heavily', 'cold sweats',
            'headache persistent', 'headaches daily',
            'mood changes', 'irritable often', 'mood swings',
            'sleep problems', 'can\'t sleep', 'insomnia',
            'appetite changes', 'not hungry', 'eating too much'
        ]
    
    def check_emergency_situation(self, user_input):
        """
        Check for emergency, warning, or concerning situations
        
        Returns:
            dict: {
                'is_emergency': bool,
                'urgency_level': str,  # 'EMERGENCY', 'HIGH', 'MODERATE', 'NORMAL'
                'message': str,
                'keywords_found': list
            }
        """
        user_text = user_input.lower()
        
        # Check for emergency situations
        emergency_found = []
        for keyword in self.emergency_keywords:
            if keyword in user_text:
                emergency_found.append(keyword)
        
        if emergency_found:
            return {
                'is_emergency': True,
                'urgency_level': 'EMERGENCY',
                'message': '🚨 **MEDICAL EMERGENCY**: What you\'re describing sounds like a serious medical emergency. Please call 911 (or your local emergency number) immediately or go to the nearest emergency room right now. Do not delay - your safety is the top priority.',
                'keywords_found': emergency_found
            }
        
        # Check for high-priority warnings
        warning_found = []
        for keyword in self.warning_keywords:
            if keyword in user_text:
                warning_found.append(keyword)
        
        if warning_found:
            return {
                'is_emergency': False,
                'urgency_level': 'HIGH',
                'message': '⚠️ **Important**: What you\'re describing needs prompt medical attention. Please contact your healthcare provider or diabetes care team as soon as possible today. If it\'s after hours, consider calling their emergency line or visiting an urgent care center.',
                'keywords_found': warning_found
            }
        
        # Check for moderate concerns
        moderate_found = []
        for keyword in self.moderate_concern_keywords:
            if keyword in user_text:
                moderate_found.append(keyword)
        
        if moderate_found:
            return {
                'is_emergency': False,
                'urgency_level': 'MODERATE',
                'message': '💛 **Keep an eye on this**: What you\'re describing is worth monitoring. Consider discussing this with your healthcare provider at your next appointment, or sooner if it gets worse or doesn\'t improve.',
                'keywords_found': moderate_found
            }
        
        # No concerning keywords found
        return {
            'is_emergency': False,
            'urgency_level': 'NORMAL',
            'message': '',
            'keywords_found': []
        }
    
    def add_medical_disclaimer(self, response, language="English"):
        """Add appropriate medical disclaimer to response"""
        disclaimers = {
            "English": "📋 **Medical Disclaimer**: This information is for educational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment. Always consult your healthcare provider for medical decisions.",
            "Spanish": "📋 **Descargo médico**: Esta información es solo para fines educativos y no sustituye el consejo, diagnóstico o tratamiento médico profesional. Siempre consulte a su proveedor de atención médica para decisiones médicas.",
            "French": "📋 **Avertissement médical**: Ces informations sont uniquement à des fins éducatives et ne remplacent pas les conseils, diagnostics ou traitements médicaux professionnels. Consultez toujours votre professionnel de santé pour les décisions médicales.",
            "Arabic": "📋 **إخلاء طبي**: هذه المعلومات لأغراض تعليمية فقط وليست بديلاً عن المشورة الطبية المهنية أو التشخيص أو العلاج. استشر دائماً مقدم الرعاية الصحية الخاص بك للقرارات الطبية.",
            "Portuguese": "📋 **Aviso médico**: Esta informação é apenas para fins educacionais e não substitui aconselhamento, diagnóstico ou tratamento médico profissional. Sempre consulte seu profissional de saúde para decisões médicas.",
            "German": "📋 **Medizinischer Haftungsausschluss**: Diese Informationen dienen nur Bildungszwecken und ersetzen keine professionelle medizinische Beratung, Diagnose oder Behandlung. Konsultieren Sie immer Ihren Arzt für medizinische Entscheidungen."
        }
        
        disclaimer = disclaimers.get(language, disclaimers["English"])
        return response + f"\n\n{disclaimer}"
    
    def get_emergency_contacts_message(self, country_code="US"):
        """Get emergency contact information based on location"""
        emergency_numbers = {
            "US": "911",
            "CA": "911", 
            "UK": "999",
            "AU": "000",
            "DE": "112",
            "FR": "112",
            "ES": "112",
            "IT": "112",
            "NL": "112",
            "IN": "102 (Ambulance) or 108",
            "MX": "911",
            "BR": "192 (Ambulance)",
            "AR": "107 (Ambulance)",
            "JP": "119 (Ambulance)",
            "KR": "119 (Ambulance)",
            "CN": "120 (Ambulance)"
        }
        
        emergency_number = emergency_numbers.get(country_code, "your local emergency number")
        
        return f"""
        🚨 **Emergency Contacts:**
        • Emergency Services: {emergency_number}
        • Poison Control (US): 1-800-222-1222
        • Crisis Text Line: Text HOME to 741741
        
        **For Diabetes Emergencies:**
        • Have someone call emergency services
        • If conscious and blood sugar is low: consume 15g fast-acting carbs
        • If unconscious: DO NOT give anything by mouth - wait for emergency services
        """
    
    def check_medication_interactions(self, user_input):
        """Check for potential medication-related concerns"""
        medication_concerns = [
            'double dose', 'took twice', 'overdose', 'too much insulin',
            'missed insulin', 'forgot medication', 'ran out of',
            'expired medication', 'old insulin', 'medication reaction',
            'allergic reaction', 'rash from', 'side effects'
        ]
        
        user_text = user_input.lower()
        found_concerns = [concern for concern in medication_concerns if concern in user_text]
        
        if found_concerns:
            return {
                'has_medication_concern': True,
                'concerns': found_concerns,
                'message': '💊 **Medication Concern Detected**: Please contact your healthcare provider or pharmacist immediately about medication-related issues. For overdose or severe reactions, seek emergency care.'
            }
        
        return {'has_medication_concern': False, 'concerns': [], 'message': ''}

# Testing and validation
if __name__ == "__main__":
    safety = MedicalSafetyGuardrails()
    
    # Test emergency scenarios
    test_cases = [
        "My blood sugar is 450 and I'm vomiting repeatedly",
        "I think I'm having diabetic ketoacidosis",
        "Blood sugar over 300 and I have ketones in my urine",
        "I'm feeling a bit tired today",
        "What should I eat for breakfast?",
        "I forgot to take my insulin this morning"
    ]
    
    print("🧪 Medical Safety Testing:")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case}")
        result = safety.check_emergency_situation(test_case)
        print(f"Urgency: {result['urgency_level']}")
        if result['message']:
            print(f"Message: {result['message'][:100]}...")
        
        # Test medication concerns
        med_result = safety.check_medication_interactions(test_case)
        if med_result['has_medication_concern']:
            print(f"Medication Concern: {med_result['message'][:50]}...")
    
    print("\n✅ Safety testing complete!")
