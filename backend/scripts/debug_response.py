import requests
import json

url = "http://localhost:8000/api/ask"
question = "Vivo en Zaragoza y gané 35000 euros en 2024, ¿cuánto pagaré de IRPF?"

print(f"\n🧪 Testing: {question}\n")

try:
    response = requests.post(url, json={"question": question}, timeout=90)
    
    print(f"Status: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        answer = data.get('answer', 'NO ANSWER')
        
        print(f"ANSWER:\n{answer}\n")
        
        # Check calculator usage
        if '13,9' in answer or 'cuota estatal' in answer.lower() or '7,1' in answer:
            print("✅ CALCULATOR WAS USED!")
        elif 'Error:' in answer:
            print("❌ Error in response")
        else:
            print("⚠️  RAG fallback (calculator not called)")
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()
