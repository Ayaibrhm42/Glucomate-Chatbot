import boto3

def test_translation():
    translate = boto3.client('translate', region_name='us-east-1')
    
    # Test text
    diabetes_text = "What is diabetes and how can I manage it?"
    
    languages = [
        ('Arabic', 'ar'),
        ('French', 'fr'), 
        ('Spanish', 'es')
    ]
    
    print("🌍 Testing Translation Capabilities:")
    print(f"Original (English): {diabetes_text}\n")
    
    for lang_name, lang_code in languages:
        try:
            response = translate.translate_text(
                Text=diabetes_text,
                SourceLanguageCode='en',
                TargetLanguageCode=lang_code
            )
            print(f"{lang_name}: {response['TranslatedText']}")
        except Exception as e:
            print(f"{lang_name}: Translation failed - {e}")
    
    print("\n✅ Translation test complete!")

if __name__ == "__main__":
    test_translation()
