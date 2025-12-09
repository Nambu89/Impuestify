"""
Quick test script to verify OpenAI connection.

Run this to test if your OpenAI API key works correctly.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

def test_openai_connection():
    """Test OpenAI API connection."""
    
    # Get credentials
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in .env")
        print("   Add: OPENAI_API_KEY=sk-proj-your-key-here")
        return False
    
    print(f"🔑 API Key found: {api_key[:10]}...{api_key[-4:]}")
    print(f"🤖 Model: {model}")
    print("\n📡 Testing OpenAI connection...\n")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Make a simple test request
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello! Connection successful.' in Spanish."}
            ],
            max_completion_tokens=50,
            temperature=1.0
        )
        
        # Extract response
        answer = response.choices[0].message.content
        
        print("✅ CONNECTION SUCCESSFUL!\n")
        print(f"📝 Response from {model}:")
        print(f"   {answer}\n")
        print(f"📊 Tokens used: {response.usage.total_tokens}")
        print(f"   - Prompt: {response.usage.prompt_tokens}")
        print(f"   - Completion: {response.usage.completion_tokens}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ CONNECTION FAILED!\n")
        print(f"Error: {str(e)}\n")
        
        # Provide helpful error messages
        if "invalid_api_key" in str(e).lower():
            print("💡 Tip: Check your OPENAI_API_KEY is correct")
        elif "model_not_found" in str(e).lower():
            print(f"💡 Tip: Model '{model}' may not be available")
            print("   Try: gpt-4o-mini, gpt-4o, or gpt-3.5-turbo")
        elif "quota" in str(e).lower():
            print("💡 Tip: You may have exceeded your API quota or need billing set up")
            
        return False


if __name__ == "__main__":
    print("="*60)
    print("🧪 OpenAI Connection Test")
    print("="*60 + "\n")
    
    success = test_openai_connection()
    
    print("="*60)
    if success:
        print("✅ All tests passed! OpenAI is ready to use.")
    else:
        print("❌ Tests failed. Fix the issues above and try again.")
    print("="*60)
