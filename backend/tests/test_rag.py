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
import pytest
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

# sentence_transformers pulls in bs4 which may be a mock in unit-test environments,
# causing "ValueError: bs4.__spec__ is None". Guard the import so collection
# succeeds even when the package or its deps are absent.
try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except (ImportError, ValueError):
    SentenceTransformer = None  # type: ignore
    _SENTENCE_TRANSFORMERS_AVAILABLE = False

from app.database.turso_client import TursoClient
from app.agents.tax_agent import get_tax_agent


class RAGSearch:
    """Busqueda semantica en la base de datos de TaxIA."""

    def __init__(self):
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            raise RuntimeError("sentence_transformers not available")
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

        Como Turso no tiene busqueda vectorial nativa aun,
        hacemos una busqueda aproximada con cosine similarity en Python.
        """
        # Generar embedding de la consulta
        query_embedding = self.model.encode(query).tolist()

        # Obtener todos los embeddings (en produccion usariamos indice vectorial)
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
            except Exception:
                continue

        # Ordenar por similitud y devolver top_k
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates[:top_k]

    async def close(self):
        await self.client.disconnect()


async def _run_rag_test(query: str):
    """Test completo del RAG (internal helper)."""
    print("=" * 60)
    print("TaxIA - Test del Sistema RAG")
    print("=" * 60)
    print(f"\nConsulta: {query}\n")

    # 1. Busqueda semantica
    print("Buscando documentos relevantes...")
    search = RAGSearch()
    await search.connect()

    results = await search.search(query, top_k=5)

    if not results:
        print("No se encontraron documentos relevantes")
        return

    print(f"Encontrados {len(results)} chunks relevantes:\n")

    for i, r in enumerate(results, 1):
        print(f"   [{i}] {r['filename']}")
        print(f"       Similitud: {r['similarity']:.3f}")
        print(f"       Pagina: {r['page_number']}")
        print(f"       Preview: {r['content'][:100]}...")
        print()

    # 2. Construir contexto
    context = "\n\n---\n\n".join([
        f"**Documento:** {r['filename']} (Pagina {r['page_number']})\n\n{r['content']}"
        for r in results
    ])

    sources = [
        {"filename": r["filename"], "page": r["page_number"], "similarity": r["similarity"]}
        for r in results
    ]

    # 3. Consultar al LLM
    print("-" * 60)
    print("Consultando al agente TaxIA...")
    print("-" * 60)

    agent = get_tax_agent()
    response = await agent.run(query, context=context, sources=sources)

    print("\nRESPUESTA:\n")
    print(response.content)

    print("\n" + "=" * 60)
    print("Fuentes utilizadas:")
    for s in sources[:3]:
        print(f"   - {s['filename']} (pag. {s['page']}, similitud: {s['similarity']:.2f})")
    print("=" * 60)

    await search.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("TURSO_DATABASE_URL") or not _SENTENCE_TRANSFORMERS_AVAILABLE,
    reason="Requires TURSO_DATABASE_URL and sentence_transformers (integration test)"
)
async def test_rag():
    """Integration test: full RAG pipeline (needs Turso credentials)."""
    query = "¿Cual es el tipo general del IVA en Espana para 2025?"
    await _run_rag_test(query)


if __name__ == "__main__":
    # Pregunta de prueba
    query = "¿Cual es el tipo general del IVA en Espana para 2025?"

    asyncio.run(_run_rag_test(query))
