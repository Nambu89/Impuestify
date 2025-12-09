"""
Test completo del sistema RAG de TaxIA.

1. Genera embedding para la consulta
2. Busca chunks similares en Turso
3. Pasa el contexto al LLM
4. Devuelve respuesta con fuentes
"""
import asyncio
import json
import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

from sentence_transformers import SentenceTransformer
from app.database.turso_client import TursoClient
from app.agents.tax_agent import get_tax_agent


class RAGSearch:
    """Búsqueda semántica en la base de datos de TaxIA."""
    
    def __init__(self):
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.client = None
    
    async def connect(self):
        """Conectar a Turso."""
        self.client = TursoClient()
        await self.client.connect()
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Busca chunks similares a la consulta.
        
        Como Turso no tiene búsqueda vectorial nativa aún,
        hacemos una búsqueda aproximada con cosine similarity en Python.
        """
        # Generar embedding de la consulta
        query_embedding = self.model.encode(query).tolist()
        
        # Obtener todos los embeddings (en producción usaríamos índice vectorial)
        result = await self.client.execute("""
            SELECT 
                e.id as emb_id,
                e.chunk_id,
                e.embedding,
                c.content,
                c.page_number,
                d.filename,
                d.title,
                d.document_type
            FROM embeddings e
            JOIN document_chunks c ON e.chunk_id = c.id
            JOIN documents d ON c.document_id = d.id
            LIMIT 2000
        """)
        
        if not result.rows:
            return []
        
        # Calcular similitud coseno
        import numpy as np
        
        candidates = []
        for row in result.rows:
            try:
                # Parsear embedding JSON - rows are dicts
                stored_embedding = json.loads(row['embedding'])
                
                # Calcular cosine similarity
                query_vec = np.array(query_embedding)
                stored_vec = np.array(stored_embedding)
                
                similarity = np.dot(query_vec, stored_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
                )
                
                candidates.append({
                    "chunk_id": row['chunk_id'],
                    "content": row['content'],
                    "page_number": row['page_number'],
                    "filename": row['filename'],
                    "title": row['title'],
                    "document_type": row['document_type'],
                    "similarity": float(similarity)
                })
            except Exception as e:
                continue
        
        # Ordenar por similitud y devolver top_k
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates[:top_k]
    
    async def close(self):
        await self.client.disconnect()


async def test_rag(query: str):
    """Test completo del RAG."""
    print("=" * 60)
    print("TaxIA - Test del Sistema RAG")
    print("=" * 60)
    print(f"\n📝 Consulta: {query}\n")
    
    # 1. Búsqueda semántica
    print("🔍 Buscando documentos relevantes...")
    search = RAGSearch()
    await search.connect()
    
    results = await search.search(query, top_k=5)
    
    if not results:
        print("❌ No se encontraron documentos relevantes")
        return
    
    print(f"✓ Encontrados {len(results)} chunks relevantes:\n")
    
    for i, r in enumerate(results, 1):
        print(f"   [{i}] {r['filename']}")
        print(f"       Similitud: {r['similarity']:.3f}")
        print(f"       Página: {r['page_number']}")
        print(f"       Preview: {r['content'][:100]}...")
        print()
    
    # 2. Construir contexto
    context = "\n\n---\n\n".join([
        f"**Documento:** {r['filename']} (Página {r['page_number']})\n\n{r['content']}"
        for r in results
    ])
    
    sources = [
        {"filename": r["filename"], "page": r["page_number"], "similarity": r["similarity"]}
        for r in results
    ]
    
    # 3. Consultar al LLM
    print("-" * 60)
    print("🤖 Consultando al agente TaxIA...")
    print("-" * 60)
    
    agent = get_tax_agent()
    response = await agent.run(query, context=context, sources=sources)
    
    print("\n📋 RESPUESTA:\n")
    print(response.content)
    
    print("\n" + "=" * 60)
    print("📚 Fuentes utilizadas:")
    for s in sources[:3]:
        print(f"   - {s['filename']} (pág. {s['page']}, similitud: {s['similarity']:.2f})")
    print("=" * 60)
    
    await search.close()


if __name__ == "__main__":
    # Pregunta de prueba
    query = "¿Cuál es el tipo general del IVA en España para 2025?"
    
    asyncio.run(test_rag(query))
