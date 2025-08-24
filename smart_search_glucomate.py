"""
GlucoMate Level 4: Smart Search Integration
Inherits: Bedrock core, safety, multilingual, knowledge base
Adds: Google Custom Search, real-time research, query classification
"""

import boto3
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build
from knowledge_enhanced_glucomate import KnowledgeEnhancedGlucoMate

# Load environment variables
load_dotenv()

class SmartMedicalSearchGlucoMate(KnowledgeEnhancedGlucoMate):
    """
    Level 4: Adds smart web search capabilities
    Inherits: Bedrock core, safety, multilingual, knowledge base
    Adds: Google Custom Search, real-time research, query classification
    """
    
    def __init__(self):
        super().__init__()  # Get ALL previous functionality
        
        # Get search credentials from environment variables
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = os.getenv('SEARCH_ENGINE_ID')
        
        # Initialize Google Search
        self.search_service = None
        try:
            if self.google_api_key and self.search_engine_id:
                self.search_service = build("customsearch", "v1", developerKey=self.google_api_key)
                print("🔍 Connected to trusted medical search sources")
            else:
                print("💭 Web search not configured - using knowledge base only")
        except Exception as e:
            self.search_service = None
            print(f"💭 Search temporarily unavailable: {str(e)[:50]}...")
        
        # Current information indicators
        self.current_info_keywords = [
            'latest', 'recent', 'new', 'current', '2024', '2025', 'breakthrough',
            'study', 'research', 'trial', 'approved', 'fda', 'updated', 'news',
            'this year', 'recently', 'just released', 'emerging'
        ]
        
        # Trusted medical domains for source verification
        self.trusted_domains = {
            'diabetes.org': 'American Diabetes Association',
            'who.int': 'World Health Organization',
            'cdc.gov': 'Centers for Disease Control',
            'nih.gov': 'National Institutes of Health',
            'pubmed.ncbi.nlm.nih.gov': 'PubMed Medical Research',
            'mayoclinic.org': 'Mayo Clinic',
            'clevelandclinic.org': 'Cleveland Clinic',
            'joslin.org': 'Joslin Diabetes Center',
            'niddk.nih.gov': 'National Institute of Diabetes',
            'jdrf.org': 'JDRF (Type 1 Diabetes Research)',
            'diabetesresearch.org': 'Diabetes Research Institute'
        }
        
        print("🌐 GlucoMate Level 4: Smart web search integration loaded")
    
    def classify_search_need(self, question):
        """
        Classify if question needs current web information
        
        Args:
            question (str): User's question
            
        Returns:
            str: 'current_medical', 'medical', 'casual'
        """
        question_lower = question.lower()
        
        # Check for current information indicators
        if any(keyword in question_lower for keyword in self.current_info_keywords):
            return 'current_medical'
        
        # Use inherited classification for other types
        return self.classify_conversation_type(question)
    
    def create_search_query(self, user_question):
        """
        Create optimized search query for medical information
        
        Args:
            user_question (str): Original user question
            
        Returns:
            str: Optimized search query
        """
        # Add diabetes context for better results
        if 'diabetes' not in user_question.lower():
            search_query = f"diabetes {user_question}"
        else:
            search_query = user_question
        
        # Add site restrictions for trusted sources
        trusted_sites = " OR ".join([f"site:{domain}" for domain in list(self.trusted_domains.keys())[:5]])
        search_query = f"{search_query} ({trusted_sites})"
        
        print(f"🔍 Search query: {search_query}")
        return search_query
    
    def search_trusted_medical_sources(self, query):
        """
        Search trusted medical sources with error handling
        
        Args:
            query (str): Search query
            
        Returns:
            str: Processed search results or None if failed
        """
        if not self.search_service:
            return None
            
        try:
            search_query = self.create_search_query(query)
            result = self.search_service.cse().list(
                q=search_query, 
                cx=self.search_engine_id, 
                num=5
            ).execute()
            
            if 'items' in result:
                return self.process_search_results(result['items'], query)
            else:
                print("🔍 No search results found")
                return None
                
        except Exception as e:
            error_str = str(e)
            if "quota" in error_str.lower():
                return "I've reached my daily search limit, but let me check my medical knowledge base for you."
            elif "invalid" in error_str.lower():
                print("🔍 Search query invalid, trying knowledge base instead")
                return None
            else:
                print(f"🔍 Search error: {error_str[:50]}...")
                return None
    
    def process_search_results(self, results, original_query):
        """
        Process and synthesize search results
        
        Args:
            results (list): Search result items
            original_query (str): Original user query
            
        Returns:
            str: Synthesized response from search results
        """
        try:
            compiled_info = []
            trusted_sources = []
            
            for result in results:
                # Extract domain and verify trustworthiness
                try:
                    domain = result['link'].split('/')[2]
                    source_name = self.get_source_name(domain)
                    
                    compiled_info.append({
                        "title": result.get('title', 'No title'),
                        "snippet": result.get('snippet', 'No snippet'),
                        "source": source_name,
                        "url": result['link'],
                        "trusted": domain in self.trusted_domains
                    })
                    
                    if domain in self.trusted_domains:
                        trusted_sources.append(source_name)
                        
                except Exception as e:
                    print(f"Error processing result: {e}")
                    continue
            
            if not compiled_info:
                return None
            
            # Create synthesis prompt with search results
            synthesis_prompt = f"""
            You are GlucoMate, a warm and caring diabetes companion. A person asked: "{original_query}"
            
            Based on these current medical sources:
            {json.dumps(compiled_info, indent=2)}
            
            Please synthesize this information into a warm, conversational response that:
            1. Acknowledges their question with empathy
            2. Provides clear, helpful information from the sources
            3. Prioritizes information from trusted medical sources
            4. Uses encouraging, supportive language
            5. Includes practical tips they can use
            6. Shows you care about their wellbeing
            7. Sounds like a knowledgeable friend, not a medical textbook
            8. Keeps all medical accuracy while being warm and personal
            9. Mentions that this is current/recent information when relevant
            
            Start with a caring acknowledgment, then provide the helpful information conversationally.
            """
            
            # Use inherited Bedrock calling method
            response = self.call_bedrock_model(
                synthesis_prompt, 
                conversation_type="medical",
                temperature=0.3  # Balance accuracy with warmth
            )
            
            # Add source attribution
            if trusted_sources:
                source_attribution = f"\n\n🌐 **Current Sources**: I found this recent information from trusted sources including {', '.join(trusted_sources[:2])}."
            else:
                source_attribution = f"\n\n🌐 **Sources**: Information from current medical research and healthcare websites."
            
            print("✨ Synthesized response from current medical sources!")
            return response + source_attribution
            
        except Exception as e:
            print(f"❌ Error processing search results: {e}")
            return None
    
    def get_source_name(self, domain):
        """Convert domain to friendly source names"""
        return self.trusted_domains.get(domain, f"medical website ({domain})")
    
    def smart_search_chat(self, user_input, target_language_code, auto_detect=False):
        """
        Smart chat with web search + all inherited features
        
        Args:
            user_input (str): User's input
            target_language_code (str): Target language code
            auto_detect (bool): Whether to auto-detect language
            
        Returns:
            str: Response with smart search enhancement
        """
        
        # Handle language detection (inherited)
        if auto_detect:
            detected_language = self.detect_language(user_input)
            if detected_language != target_language_code:
                print(f"🔍 Detected language: {detected_language}")
                target_language_code = detected_language
        
        # Translate to English for processing (inherited)
        english_input = self.translate_to_english(user_input, target_language_code)
        
        # Safety check first (inherited)
        safety_check = self.check_safety(english_input)
        
        if safety_check['is_emergency']:
            emergency_msg = safety_check['message']
            if target_language_code != 'en':
                emergency_msg = self.translate_response(emergency_msg, target_language_code)
            return emergency_msg
        
        # Get language name
        language_name = "English"
        for code, (name, lang_code) in self.supported_languages.items():
            if lang_code == target_language_code:
                language_name = name
                break
        
        # Classify search need
        search_classification = self.classify_search_need(english_input)
        response = None
        
        print("💭 Analyzing your question...")
        
        # Handle casual conversation (inherited)
        if search_classification == "casual":
            return self.multilingual_chat(user_input, target_language_code, auto_detect)
        
        # For current medical info, try web search first
        if search_classification == "current_medical" and self.search_service:
            print("🌐 Searching for the latest medical information...")
            web_response = self.search_trusted_medical_sources(english_input)
            if web_response:
                print("✅ Found current information from trusted sources!")
                response = web_response
        
        # Try knowledge base if no web response (inherited)
        if not response:
            print("📚 Checking medical knowledge base...")
            kb_response = self.query_medical_knowledge(english_input)
            if kb_response:
                print("✅ Found authoritative information!")
                
                # Enhance KB response with conversational tone (inherited method)
                enhancement_prompt = self.create_knowledge_enhanced_prompt(
                    english_input, kb_response, language_name
                )
                response = self.call_bedrock_model(
                    enhancement_prompt, 
                    conversation_type="medical"
                )
        
        # Final fallback to multilingual chat (inherited)
        if not response:
            print("🧠 Using comprehensive medical knowledge...")
            return self.knowledge_enhanced_chat(user_input, target_language_code, auto_detect)
        
        # Add encouragement if needed (inherited)
        if any(word in english_input.lower() for word in ['scared', 'worried', 'difficult', 'hard', 'confused']):
            encouragement = "\n\n" + self.encouragement[hash(english_input) % len(self.encouragement)]
            response = response + encouragement
        
        # Translate response (inherited method)
        if target_language_code != 'en':
            response = self.enhance_medical_translation(response, target_language_code)
        
        # Add medical disclaimer (inherited method)
        response = self.add_medical_disclaimer(response, language_name)
        
        # Add safety warnings if needed (inherited)
        if safety_check['urgency_level'] in ['HIGH', 'MODERATE']:
            warning_msg = safety_check['message']
            if target_language_code != 'en':
                warning_msg = self.translate_response(warning_msg, target_language_code)
            response = warning_msg + "\n\n" + response
        
        return response
    
    def test_search_capability(self):
        """Test web search functionality"""
        print("🧪 Testing web search capability...")
        
        if not self.search_service:
            print("❌ Web search not available")
            return False
        
        try:
            test_query = "latest diabetes research 2024"
            result = self.search_trusted_medical_sources(test_query)
            
            if result:
                print("✅ Web search connection successful!")
                return True
            else:
                print("⚠️ Web search returned no results")
                return False
                
        except Exception as e:
            print(f"❌ Web search test failed: {e}")
            return False
    
    def get_search_stats(self):
        """Get search capability information"""
        return {
            'search_available': self.search_service is not None,
            'trusted_domains': len(self.trusted_domains),
            'current_keywords': len(self.current_info_keywords),
            'google_api_configured': bool(self.google_api_key),
            'search_engine_configured': bool(self.search_engine_id)
        }

def main():
    """Demo of Level 4 - Smart Search GlucoMate"""
    print("🌐 GlucoMate Level 4: Smart Medical Search Integration")
    print("🔍 Now with real-time medical research and current information!")
    print("\n✨ New Features:")
    print("   • Google Custom Search for latest medical research")
    print("   • Trusted medical source verification")
    print("   • Current information detection and retrieval")
    print("   • Multi-source information synthesis")
    print("   • All previous features (multilingual, knowledge base)")
    
    bot = SmartMedicalSearchGlucoMate()
    
    # Test capabilities
    search_stats = bot.get_search_stats()
    print(f"\n📊 Search Capabilities:")
    print(f"   • Web Search Available: {'✅' if search_stats['search_available'] else '❌'}")
    print(f"   • Trusted Medical Domains: {search_stats['trusted_domains']}")
    print(f"   • Current Info Keywords: {search_stats['current_keywords']}")
    
    if search_stats['search_available']:
        bot.test_search_capability()
    else:
        print("\n⚠️ Web search not configured. Set GOOGLE_API_KEY and SEARCH_ENGINE_ID in .env")
        print("   The system will use knowledge base and multilingual features.")
    
    # Test knowledge base (inherited)
    print("\n📚 Testing knowledge base...")
    if not bot.test_knowledge_base_connection():
        print("⚠️ Knowledge base issues detected")
    
    # Language selection (inherited)
    language_name, language_code = bot.get_language_choice()
    
    # Cultural greeting (inherited)
    greeting = bot.get_cultural_greeting(language_code)
    print(f"\n💙 {greeting}")
    
    # Auto-detect option (inherited)
    auto_detect_prompt = "Enable automatic language detection? (y/n): "
    if language_code != 'en':
        auto_detect_prompt = bot.translate_response(auto_detect_prompt, language_code)
    auto_detect = input(f"🔍 {auto_detect_prompt}").lower().startswith('y')
    
    # Smart search suggestions
    search_suggestions = [
        "What's the latest diabetes research in 2024?",
        "Recent breakthrough treatments for Type 1 diabetes",
        "Current FDA-approved diabetes medications",
        "New diabetes technology this year",
        "What are normal blood sugar levels?"  # Knowledge base query
    ]
    
    print(f"\n💡 Try asking about current medical topics:")
    for suggestion in search_suggestions[:3]:
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
                farewell = bot.get_cultural_farewell(language_code)
                print(f"\n💙 GlucoMate: {farewell}")
                break
            
            if user_input:
                response = bot.smart_search_chat(user_input, language_code, auto_detect)
                print(f"\n🌐 GlucoMate: {response}")
                print("\n" + "─" * 60)
            else:
                ready_msg = "I'm here with the latest medical information and research!"
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
