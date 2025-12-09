"""
Pipeline de extracción de PDFs para TaxIA.

Extrae contenido de PDFs usando Azure Document Intelligence,
crea chunks y genera embeddings para almacenar en Turso.

Ejecutar desde el directorio backend:
    python scripts/extract_pdfs.py
"""
import asyncio
import os
import sys
import uuid
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Añadir el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)


@dataclass
class ExtractedChunk:
    """Chunk extraído de un documento."""
    content: str
    page_number: int
    chunk_index: int
    section_title: Optional[str] = None


class AzureDocumentExtractor:
    """Extractor de PDFs usando Azure Document Intelligence."""
    
    def __init__(self):
        self.endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        self.client = None
        
        if not self.endpoint or not self.key:
            raise ValueError(
                "Azure Document Intelligence no configurado.\n"
                "Configura AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT y AZURE_DOCUMENT_INTELLIGENCE_KEY en .env"
            )
    
    def _init_client(self):
        """Inicializa el cliente de Azure Document Intelligence."""
        if self.client is None:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key)
            )
    
    def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extrae texto de un PDF usando Azure Document Intelligence.
        
        Returns:
            Dict con 'pages', 'total_pages', 'sections'
        """
        self._init_client()
        
        import base64
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        
        # Leer archivo y codificar en base64
        with open(pdf_path, "rb") as f:
            file_content = f.read()
        
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        # Crear request con bytes_source (SDK v4.0)
        poller = self.client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=AnalyzeDocumentRequest(
                bytes_source=base64_content
            )
        )
        
        result = poller.result()
        
        pages = []
        for page in result.pages:
            page_text = ""
            if page.lines:
                page_text = "\n".join([line.content for line in page.lines])
            pages.append({
                "page_number": page.page_number,
                "content": page_text
            })
        
        # Extraer secciones/encabezados
        sections = []
        if hasattr(result, 'paragraphs') and result.paragraphs:
            for para in result.paragraphs:
                if hasattr(para, 'role') and para.role in ['title', 'sectionHeading']:
                    page_num = 1
                    if para.bounding_regions:
                        page_num = para.bounding_regions[0].page_number
                    sections.append({
                        "title": para.content,
                        "page": page_num
                    })
        
        return {
            "pages": pages,
            "total_pages": len(pages),
            "sections": sections
        }


class TextChunker:
    """
    Divide texto en chunks semánticos para RAG.
    
    Características:
    - Respeta límites de oraciones (nunca corta a mitad de frase)
    - Usa secciones del documento si están disponibles
    - Overlap inteligente para mantener contexto
    - Validación de calidad de chunks
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # Patrón regex para detectar finales de oraciones en español
        import re
        self.sentence_end_pattern = re.compile(
            r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])|'  # Punto/signo seguido de mayúscula
            r'(?<=\.)\s*\n|'                    # Punto seguido de salto de línea
            r'(?<=[.!?])\s+(?=\d)|'             # Punto seguido de número (artículos)
            r'(?<=:)\s*\n'                       # Dos puntos seguidos de salto
        )
    
    def chunk_document(
        self, 
        pages: List[Dict],
        sections: List[Dict] = None
    ) -> List[ExtractedChunk]:
        """
        Divide un documento en chunks semánticos.
        
        Args:
            pages: Lista de páginas con 'content' y 'page_number'
            sections: Secciones detectadas por Document Intelligence
        """
        chunks = []
        chunk_index = 0
        
        # Combinar todo el texto preservando información de página
        full_text = ""
        page_boundaries = []  # [(start_char, end_char, page_num), ...]
        
        for page in pages:
            start = len(full_text)
            page_content = page["content"].strip()
            if page_content:
                full_text += page_content + "\n\n"
            end = len(full_text)
            page_boundaries.append((start, end, page["page_number"]))
        
        # Dividir en oraciones primero
        sentences = self._split_into_sentences(full_text)
        
        # Agrupar oraciones en chunks
        current_chunk = ""
        current_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Si añadir esta oración excede el tamaño
            if len(current_chunk) + len(sentence) + 1 > self.chunk_size:
                # Guardar chunk actual si tiene contenido suficiente
                if len(current_chunk) >= self.min_chunk_size:
                    page_num = self._get_page_for_position(
                        len(full_text) - len(current_chunk) - len(sentence),
                        page_boundaries
                    )
                    chunks.append(ExtractedChunk(
                        content=current_chunk.strip(),
                        page_number=page_num,
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
                    
                    # Overlap: mantener últimas oraciones para contexto
                    overlap_text = self._get_overlap_text(current_sentences)
                    current_chunk = overlap_text + " " + sentence if overlap_text else sentence
                    current_sentences = [sentence]
                else:
                    # Chunk muy pequeño, seguir añadiendo
                    current_chunk += " " + sentence
                    current_sentences.append(sentence)
            else:
                current_chunk += (" " if current_chunk else "") + sentence
                current_sentences.append(sentence)
        
        # Añadir último chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            page_num = self._get_page_for_position(
                len(full_text) - len(current_chunk),
                page_boundaries
            )
            chunks.append(ExtractedChunk(
                content=current_chunk.strip(),
                page_number=page_num,
                chunk_index=chunk_index
            ))
        
        # Validar y limpiar chunks
        chunks = self._validate_chunks(chunks)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Divide texto en oraciones respetando la gramática española.
        """
        import re
        
        # Proteger abreviaturas comunes para no dividir incorrectamente
        text = text.replace("Art.", "Art·")
        text = text.replace("art.", "art·")
        text = text.replace("Núm.", "Núm·")
        text = text.replace("núm.", "núm·")
        text = text.replace("Mod.", "Mod·")
        text = text.replace("mod.", "mod·")
        text = text.replace("etc.", "etc·")
        text = text.replace("p.ej.", "p·ej·")
        text = text.replace("Ej.", "Ej·")
        
        # Dividir por fin de oración
        sentences = self.sentence_end_pattern.split(text)
        
        # Restaurar abreviaturas
        sentences = [s.replace("·", ".") for s in sentences]
        
        # Filtrar oraciones vacías y muy cortas
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        return sentences
    
    def _get_overlap_text(self, sentences: List[str]) -> str:
        """Obtiene texto de overlap de las últimas oraciones."""
        if not sentences:
            return ""
        
        overlap = ""
        for sentence in reversed(sentences):
            if len(overlap) + len(sentence) <= self.chunk_overlap:
                overlap = sentence + " " + overlap
            else:
                break
        
        return overlap.strip()
    
    def _get_page_for_position(
        self, 
        char_position: int, 
        page_boundaries: List[tuple]
    ) -> int:
        """Determina a qué página pertenece una posición de carácter."""
        for start, end, page_num in page_boundaries:
            if start <= char_position < end:
                return page_num
        return page_boundaries[-1][2] if page_boundaries else 1
    
    def _validate_chunks(self, chunks: List[ExtractedChunk]) -> List[ExtractedChunk]:
        """
        Valida y limpia los chunks.
        - Elimina chunks que son solo números o caracteres especiales
        - Combina chunks muy pequeños con el siguiente
        """
        import re
        
        validated = []
        
        for chunk in chunks:
            content = chunk.content.strip()
            
            # Verificar que tiene contenido textual real
            text_only = re.sub(r'[^\w\sáéíóúñÁÉÍÓÚÑ]', '', content)
            if len(text_only) < self.min_chunk_size * 0.5:
                continue  # Saltar chunks sin suficiente texto
            
            # Verificar que no es solo encabezados o números
            words = content.split()
            if len(words) < 5:
                continue
            
            validated.append(chunk)
        
        return validated


class EmbeddingGenerator:
    """Genera embeddings usando sentence-transformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self.model = None
        self.dimensions = 384
    
    def _load_model(self):
        """Carga el modelo de embeddings."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            print(f"   📥 Cargando modelo de embeddings...")
            self.model = SentenceTransformer(self.model_name)
            print(f"   ✓ Modelo cargado ({self.dimensions} dimensiones)")
    
    def generate(self, texts: List[str]) -> List[str]:
        """Genera embeddings para una lista de textos.
        
        Returns:
            Lista de embeddings serializados como JSON string.
        """
        import json
        self._load_model()
        
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Convertir a JSON string para compatibilidad con libsql
        # (BLOB tiene problemas en la versión actual)
        return [json.dumps(emb.tolist()) for emb in embeddings]


async def process_pdfs(data_dir: str):
    """Procesa todos los PDFs en el directorio data."""
    from app.database.turso_client import TursoClient
    
    print("=" * 60)
    print("TaxIA - Extracción de PDFs con Azure Document Intelligence")
    print("=" * 60)
    
    # Inicializar componentes
    try:
        extractor = AzureDocumentExtractor()
        print("✓ Azure Document Intelligence configurado")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    embedder = EmbeddingGenerator()
    
    # Conectar a Turso
    print("\n📡 Conectando a Turso...")
    client = TursoClient()
    await client.connect()
    print("✓ Conexión establecida\n")
    
    # Obtener lista de PDFs
    data_path = Path(data_dir)
    pdf_files = list(data_path.glob("*.pdf"))
    
    print(f"📚 Encontrados {len(pdf_files)} archivos PDF\n")
    
    total_chunks = 0
    processed_docs = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] 📄 {pdf_file.name}")
        
        try:
            # Calcular hash del archivo
            file_hash = hashlib.md5(pdf_file.read_bytes()).hexdigest()
            
            # Verificar si ya está procesado
            existing = await client.execute(
                "SELECT id FROM documents WHERE hash = ?",
                [file_hash]
            )
            
            if existing.rows:
                print(f"         ⏭️  Ya procesado, saltando...\n")
                continue
            
            # Extraer texto con Azure Document Intelligence
            print(f"         📖 Extrayendo con Azure Document Intelligence...")
            extracted = extractor.extract_text(str(pdf_file))
            
            if not extracted["pages"]:
                print(f"         ⚠️  No se pudo extraer texto\n")
                continue
            
            print(f"         ✓ {extracted['total_pages']} páginas extraídas")
            
            # Crear registro del documento
            doc_id = str(uuid.uuid4())
            doc_type = categorize_document(pdf_file.name)
            year = extract_year(pdf_file.name)
            
            await client.execute(
                """
                INSERT INTO documents 
                (id, filename, filepath, title, document_type, year, total_pages, file_size, hash, processed, processing_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    doc_id,
                    pdf_file.name,
                    str(pdf_file),
                    pdf_file.stem.replace("_", " "),
                    doc_type,
                    year,
                    extracted["total_pages"],
                    pdf_file.stat().st_size,
                    file_hash,
                    0,
                    "processing"
                ]
            )
            
            # Crear chunks
            print(f"         ✂️  Creando chunks...")
            chunks = chunker.chunk_document(extracted["pages"])
            print(f"         ✓ {len(chunks)} chunks creados")
            
            # Insertar chunks
            chunk_ids = []
            chunk_texts = []
            
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                chunk_ids.append(chunk_id)
                chunk_texts.append(chunk.content)
                
                await client.execute(
                    """
                    INSERT INTO document_chunks 
                    (id, document_id, chunk_index, content, content_hash, page_number, token_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        chunk_id,
                        doc_id,
                        chunk.chunk_index,
                        chunk.content,
                        hashlib.md5(chunk.content.encode()).hexdigest(),
                        chunk.page_number,
                        len(chunk.content.split())
                    ]
                )
            
            # Generar e insertar embeddings
            print(f"         🧠 Generando embeddings...")
            try:
                embeddings = embedder.generate(chunk_texts)
                
                print(f"         💾 Guardando embeddings en Turso...")
                for chunk_id, embedding in zip(chunk_ids, embeddings):
                    emb_id = str(uuid.uuid4())
                    await client.execute(
                        """
                        INSERT INTO embeddings (id, chunk_id, embedding, model_name, dimensions)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        [emb_id, chunk_id, embedding, embedder.model_name, embedder.dimensions]
                    )
                
                # Marcar como procesado
                await client.execute(
                    "UPDATE documents SET processed = 1, processing_status = 'completed' WHERE id = ?",
                    [doc_id]
                )
            except Exception as emb_error:
                print(f"         ⚠️  Error en embeddings: {emb_error}")
                # Marcar con error pero documento sigue insertado
                await client.execute(
                    "UPDATE documents SET processing_status = 'partial', error_message = ? WHERE id = ?",
                    [f"Embeddings error: {str(emb_error)}", doc_id]
                )
            
            total_chunks += len(chunks)
            processed_docs += 1
            print(f"         ✅ Completado\n")
            
        except Exception as e:
            print(f"         ❌ Error: {e}\n")
            # Marcar error en BD si existe el documento
            try:
                await client.execute(
                    "UPDATE documents SET processing_status = 'error', error_message = ? WHERE filename = ?",
                    [str(e), pdf_file.name]
                )
            except:
                pass
    
    await client.disconnect()
    
    print("=" * 60)
    print(f"✅ EXTRACCIÓN COMPLETADA")
    print(f"   Documentos procesados: {processed_docs}/{len(pdf_files)}")
    print(f"   Chunks totales: {total_chunks}")
    print("=" * 60)


def categorize_document(filename: str) -> str:
    """Categoriza el documento según su nombre."""
    filename_lower = filename.lower()
    
    if "iva" in filename_lower:
        return "IVA"
    elif "renta" in filename_lower or "irpf" in filename_lower:
        return "IRPF"
    elif "sociedades" in filename_lower:
        return "IS"
    elif "patrimonio" in filename_lower:
        return "IP"
    elif "retenciones" in filename_lower:
        return "RET"
    elif "calendario" in filename_lower:
        return "CAL"
    elif "factura" in filename_lower or "verifactu" in filename_lower:
        return "FAC"
    elif "transito" in filename_lower or "aduanas" in filename_lower:
        return "ADU"
    elif "discapacidad" in filename_lower:
        return "IRPF"
    elif "mayores" in filename_lower or "65" in filename_lower:
        return "IRPF"
    elif "grandes empresas" in filename_lower:
        return "IS"
    else:
        return "GENERAL"


def extract_year(filename: str) -> Optional[int]:
    """Extrae el año del nombre del archivo."""
    import re
    match = re.search(r'20\d{2}', filename)
    return int(match.group()) if match else None


if __name__ == "__main__":
    # Ruta al directorio data
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    
    if not data_dir.exists():
        print(f"❌ Directorio no encontrado: {data_dir}")
        sys.exit(1)
    
    asyncio.run(process_pdfs(str(data_dir)))
