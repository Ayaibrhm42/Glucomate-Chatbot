import boto3
import json
import sys
import os
from googleapiclient.discovery import build
from datetime import datetime
import re
from medical_safety import MedicalSafetyGuardrails

class SmartMedicalSearchGlucoMate:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        self.translate_client = boto3.client('translate', region_name='us-east-1')
        self.safety = MedicalSafetyGuardrails()
        self.model_id = "amazon.titan-text-premier-v1:0"
        
        # Your Knowledge Base ID
        self.knowledge_base_id = "JX4DNBIXAA"
        
        # Google Custom Search Configuration
        # TODO: Replace with your actual API key and Search Engine ID
        self.google_api_key = "os.getenv('GOOGLE_API_KEY')"
        self.search_engine_id = "930f2df31ce9c4058"
        
        # Initialize Google Search
        try:
            if self.google_api_key != "AIzaSyC3SfONtBhHZ18Od19a31Dn2uUbgK5wqsQ":
                self.search_service = build("customsearch", "v1", developerKey=self.google_api_key)
            else:
                self.search_service = None
                print("⚠️ Google Search not configured - using Knowledge Base only")
        except Exception as e:
            print(f"⚠️ Google Search setup failed: {e}")
            self.search_service = None
        
        # Supported languages
        self.supported_languages = {
            '1': ('English', 'en'),
            '2': ('Arabic', 'ar'), 
            '3': ('French', 'fr'),
            '4': ('Spanish', 'es'),
            '5': ('Portuguese', 'pt'),
            '6': ('German', 'de')
        }
    
    def classify_query_type(self, question):
        """Classify if question needs current info or can use Knowledge Base"""
        current_info_keywords = [
            "latest", "recent", "new", "current", "2024", "2025", "newest",
            "updated", "breakthrough", "trial", "study", "research", 
            "medication approved", "guidelines updated", "news"
        ]
        
        question_lower = question.lower()
        needs_current_info = any(keyword in question_lower for keyword in current_info_keywords)
        
        return "current" if needs_current_info else "knowledge_base"
    
    def search_trusted_medical_sources(self, query):
        """Search only trusted medical websites using Google Custom Search"""
        if not self.search_service:
            return None
            
        try:
            # Enhanced query for diabetes-specific medical information
            search_query = f"diabetes {query}"
            
            # Perform the search
            result = self.search_service.cse().list(
                q=search_query,
                cx=self.search_engine_id,
                num=5  # Get top 5 results
            ).execute()
            
            if 'items' in result:
                return self.process_search_results(result['items'], query)
            else:
                return None
                
        except Exception as e:
            print(f"Medical web search failed: {e}")
            return None
    
    def process_search_results(self, results, original_query):
        """Process search results and generate medical response"""
        try:
            # Compile information from trusted sources
            compiled_info = []
            for result in results:
                # Extract domain for source attribution
                domain = result['link'].split('/')[2]
                source_name = self.get_source_name(domain)
                
                compiled_info.append({
                    "title": result['title'],
                    "snippet": result['snippet'],
                    "source": source_name,
                    "url": result['link'],
                    "domain": domain
                })
            
            # Use AI to synthesize information from trusted sources
            synthesis_prompt = f"""
            Based on the following information from trusted medical sources, provide a comprehensive answer to: {original_query}
            
            Search Results:
            {json.dumps(compiled_info, indent=2)}
            
            Guidelines:
            1. Synthesize information from all sources
            2. Highlight any new or updated information
            3. Maintain medical accuracy and caution
            4. Focus on diabetes-related information
            5. If results are not directly relevant, say so
            6. Be concise but comprehensive
            
            Provide a medical response based on these trusted sources:
            """
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "inputText": synthesis_prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 1500,
                        "temperature": 0.1,
                        "topP": 0.9
                    }
                }),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            synthesized_answer = response_body['results'][0]['outputText']
            
            # Add source citations
            citations = "\n\n📚 **Trusted Medical Sources:**\n"
            for info in compiled_info:
                citations += f"• {info['source']} - {info['title'][:50]}...\n"
            
            return synthesized_answer + citations
            
        except Exception as e:
            print(f"Error processing search results: {e}")
            return None
    
    def get_source_name(self, domain):
        """Convert domain to readable source name"""
        source_map = {
            "diabetes.org": "American Diabetes Association",
            "who.int": "World Health Organization",
            "cdc.gov": "Centers for Disease Control",
            "nih.gov": "National Institutes of Health",
            "pubmed.ncbi.nlm.nih.gov": "PubMed Medical Research",
            "mayoclinic.org": "Mayo Clinic",
            "clevelandclinic.org": "Cleveland Clinic",
            "joslin.org": "Joslin Diabetes Center",
            "endocrine.org": "Endocrine Society"
        }
        return source_map.get(domain, domain)
    
    def query_medical_knowledge(self, question):
        """Query the diabetes knowledge base"""
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
            
            answer = response['output']['text']
            sources = response.get('citations', [])
            
            if sources:
                source_info = "\n\n📚 **Knowledge Base Sources**: Medical guidelines and evidence-based literature."
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
                Settings={'Formality': 'FORMAL'}
            )
            return response['TranslatedText']
        except Exception as e:
            return text
    
    def smart_medical_chat(self, user_input, target_language_code):
        """Smart medical chat with both Knowledge Base and trusted web search"""
        
        # Translate input to English for processing
        english_input = self.translate_to_english(user_input, target_language_code)
        
        # Check for emergency situations first
        safety_check = self.safety.check_emergency_situation(english_input)
        
        if safety_check['is_emergency']:
            emergency_msg = safety_check['message']
            if target_language_code != 'en':
                emergency_msg = self.translate_response(emergency_msg, target_language_code)
            return emergency_msg
        
        # Classify query type
        query_type = self.classify_query_type(english_input)
        response = None
        
        if query_type == "current" and self.search_service:
            # For current information, search trusted medical sources first
            print("🔍 Searching latest medical information from trusted sources...")
            web_response = self.search_trusted_medical_sources(english_input)
            
            if web_response:
                print("✅ Found current information from trusted medical sources")
                response = web_response
            else:
                print("⚠️ Current info not found, checking knowledge base...")
                kb_response = self.query_medical_knowledge(english_input)
                response = kb_response
        else:
            # For general diabetes questions, use Knowledge Base first
            print("🔍 Searching medical knowledge base...")
            kb_response = self.query_medical_knowledge(english_input)
            
            if kb_response:
                print("✅ Response from medical knowledge base")
                response = kb_response
            elif self.search_service:
                print("🔍 Knowledge base insufficient, searching trusted medical sources...")
                web_response = self.search_trusted_medical_sources(english_input)
                response = web_response
        
        # Fallback response
        if not response:
            response = "I apologize, but I couldn't find specific information about your question. Please consult your healthcare provider for personalized medical guidance."
        
        # Translate response if needed
        if target_language_code != 'en':
            response = self.translate_response(response, target_language_code)
        
        # Add comprehensive medical disclaimer
        disclaimer = f"""

📋 **Medical Information Notice:**
- Information from trusted medical organizations and research
- Updated: {datetime.now().strftime('%Y-%m-%d')}
- This is educational information only
- Always consult your healthcare provider for personalized advice
- In emergencies, call 911 immediately

🏥 **Sources**: Knowledge Base + Trusted medical websites (ADA, WHO, CDC, NIH)"""
        
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
    print("🧠 GlucoMate with Smart Medical Search")
    print("🏥 Knowledge Base + Trusted Medical Web Search")
    print("🌍 Multilingual support available")
    
    bot = SmartMedicalSearchGlucoMate()
    
    # Check configuration
    if bot.search_service:
        print("✅ Google Medical Search: Enabled")
    else:
        print("⚠️ Google Medical Search: Not configured (using Knowledge Base only)")
        print("📋 To enable: Add your Google API key and Search Engine ID")
    
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
    print("🩺 Ask me anything about diabetes!")
    print("💡 Try: 'latest diabetes research' or 'new diabetes medications 2024'")
    print("Type 'quit' to exit\n")
    
    try:
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'stop']:
                print("GlucoMate: Take care! Stay updated with diabetes care! 👋")
                break
            
            if user_input:
                response = bot.smart_medical_chat(user_input, language_code)
                print(f"\n🩺 GlucoMate: {response}\n")
                print("-" * 60)
            else:
                print("Please enter a question or type 'quit' to exit.")
                
    except KeyboardInterrupt:
        print("\n\n🩺 GlucoMate: Goodbye! Stay healthy! 👋")

if __name__ == "__main__":
    main()
