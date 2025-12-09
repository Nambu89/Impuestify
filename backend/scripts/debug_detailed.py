"""
Ultra-simple debug test with detailed output.
"""
import requests
import json
import sys

print("\n" + "="*80)
print("🔍 DEBUGGING IRPF FUNCTION CALLING")
print("="*80 + "\n")

url = "http://localhost:8000/api/ask"
question = "Vivo en Zaragoza y gané 35000 euros en 2024, ¿cuánto pagaré de IRPF?"

print(f"Endpoint: {url}")
print(f"Question: {question}\n")
print("Sending request...")

try:
    response = requests.post(
        url, 
        json={"question": question, "k": 5},
        timeout=120
    )
    
    print(f"\n{'='*80}")
    print(f"HTTP Status: {response.status_code}")
    print(f"{'='*80}\n")
    
    if response.status_code == 200:
        data = response.json()
        
        answer = data.get('answer', '')
        processing_time = data.get('processing_time', 0)
        sources = data.get('sources', [])
        metadata = data.get('metadata', {})
        
        print(f"Processing Time: {processing_time:.2f}s")
        print(f"Sources Count: {len(sources)}")
        print(f"Metadata: {json.dumps(metadata, indent=2)}\n")
        
        print(f"{'='*80}")
        print("ANSWER:")
        print(f"{'='*80}")
        
        if answer:
            print(answer)
            print(f"\nAnswer Length: {len(answer)} chars")
            
            # Check for calculator indicators
            indicators = {
                'Has "Cuota Estatal"': 'Cuota Estatal' in answer,
                'Has "13,9"': '13,9' in answer,
                'Has "7,1"': '7,1' in answer,
                'Has "Aragón"': 'Aragón' in answer,
                'Has calculation format': '€' in answer and 'Cuota' in answer
            }
            
            print(f"\n{'='*80}")
            print("INDICATORS:")
            print(f"{'='*80}")
            for key, value in indicators.items():
                icon = "✅" if value else "❌"
                print(f"{icon} {key}: {value}")
            
            if any(indicators.values()):
                print(f"\n{'='*80}")
                print("🎉 CALCULATOR WAS USED!")
                print(f"{'='*80}")
            else:
                print(f"\n{'='*80}")
                print("⚠️  RAG FALLBACK - Calculator NOT triggered")
                print(f"{'='*80}")
        else:
            print("❌ ANSWER IS EMPTY!")
            print("\nThis is the problem we need to fix.")
            
        print(f"\n{'='*80}\n")
        
    else:
        print(f"❌ HTTP Error {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"\n❌ Exception occurred:")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
