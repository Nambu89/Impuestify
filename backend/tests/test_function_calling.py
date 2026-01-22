"""
Quick test to see if function calling is working.
"""
import requests
import json

url = "http://localhost:8000/api/ask"

data = {
    "question": "Vivo en Zaragoza y gané 35000 euros en 2024, ¿cuánto pagaré de IRPF?",
    "k": 5
}

print("\n🧪 Testing IRPF function calling...")
print(f"Query: {data['question']}\n")

try:
    response = requests.post(url, json=data, timeout=60)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ SUCCESS!")
        print(f"\nAnswer:\n{result['answer'][:500]}...")
        print(f"\nProcessing time: {result['processing_time']:.2f}s")
        print(f"Sources: {len(result['sources'])}")
        
        # Check if answer contains IRPF calculation
        if "13,994" in result['answer'] or "cuota" in result['answer'].lower():
            print("\n🎉 CALCULATOR WAS USED!")
        else:
            print("\n⚠️  Normal RAG response (calculator not triggered)")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text[:500])
        
except Exception as e:
    print(f"\n❌ Error: {e}")
