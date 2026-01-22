"""
Script to test directly via Python to see the exact response.
This confirms whether the function calling is actually working or not.
"""
import requests
import json

print("\n" + "="*70)
print("🧪 TESTING IRPF CALCULATOR FUNCTION CALLING")
print("="*70 + "\n")

url = "http://localhost:8000/api/ask"
question = "Vivo en Zaragoza y gané 35000 euros en 2024, ¿cuánto pagaré de IRPF?"

print(f"URL: {url}")
print(f"Question: {question}\n")

try:
    response = requests.post(url, json={"question": question}, timeout=90)
    
    print(f"Status Code: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        answer = data.get('answer', '')
        processing_time = data.get('processing_time', 0)
        sources = data.get('sources', [])
        
        print("="*70)
        print("FULL ANSWER:")
        print("="*70)
        print(answer)
        print("\n" + "="*70)
        
        print(f"\nProcessing time: {processing_time:.2f}s")
        print(f"Sources count: {len(sources)}\n")
        
        # Check if calculator was used
        if '13,9' in answer or '7,1' in answer or 'Cuota Estatal' in answer:
            print("✅ ✅ ✅ CALCULATOR WAS USED! ✅ ✅ ✅")
        elif 'Error:' in answer:
            print("❌ Error in response")
        else:
            print("⚠️  RAG fallback - calculator NOT called")
            print("Checking answer content:")
            print(f"  - Contains 'Cuota': {'Cuota' in answer}")
            print(f"  - Contains '13,': {'13,' in answer}")
            print(f"  - Contains 'Estatal': {'Estatal' in answer}")
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(response.text[:500])
        
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70 + "\n")
