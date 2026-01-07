
import os
import sys
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from ai_summarizer_gemini import get_gemini_client, summarize_article

def test_summary():
    print("Testing Gemini 2.0 Client (google-genai SDK)...")
    try:
        client = get_gemini_client()
        print("Client initialized.")
        
        title = "Test Article: New Drug approved"
        content = "The FDA has approved a new drug named TestD only for testing purposes. This update brings significant changes to the testing protocol." * 10
        
        print("Sending request...")
        result = summarize_article(client, title, content)
        
        if result.get('error'):
            print(f"FAILED: {result['error']}")
        else:
            print("SUCCESS!")
            print(f"Summary: {result.get('ai_summary')[:50]}...")
            print(f"Model used: {result.get('model_used')}")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_summary()
