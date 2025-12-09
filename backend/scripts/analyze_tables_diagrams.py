"""
Analyze all 26 PDFs to identify structured tables and diagrams.

Identifies:
1. Tax scale tables (IRPF, IS, etc.)
2. Deduction tables
3. Retention tables
4. Diagrams and flowcharts

Output: Report of all structured data that should be extracted to dedicated SQL tables.
"""
import asyncio
import os
import sys
import re
from pathlib import Path
from collections import defaultdict

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient


class TableDetector:
    """Detect different types of tables in document chunks."""
    
    # Patterns for different table types
    PATTERNS = {
        'escala_irpf': [
            r'base\s+liquidable|cuota\s+(?:íntegra|integra)|tipo\s+aplicable',
            r'tramo|escala.*irpf',
            r'\d+[.,]\d+\s+(?:€|euros)'
        ],
        'deducciones': [
            r'deducc[ií]on|deducible',
            r'porcentaje|límite|cuantía',
            r'base\s+(?:máxima|mínima)'
        ],
        'retenciones': [
            r'retenc[ií]on|tipo.*retenc',
            r'rendimientos.*trabajo',
            r'tabla.*retenc'
        ],
        'plazos': [
            r'plazo|fecha.*límite',
            r'modelo\s+\d+',
            r'presentac[ií]on'
        ],
        'reducciones': [
            r'reducc[ií]on',
            r'rendimientos.*trabajo|rendimientos.*capital',
            r'importe|cuantía'
        ],
        'tipos_iva': [
            r'tipo.*iva|iva.*(?:general|reducido|superreducido)',
            r'21\s*%|10\s*%|4\s*%'
        ]
    }
    
    def detect_table_type(self, text: str) -> list:
        """Detect what type(s) of table this chunk contains."""
        text_lower = text.lower()
        detected = []
        
        for table_type, patterns in self.PATTERNS.items():
            if any(re.search(pattern, text_lower) for pattern in patterns):
                detected.append(table_type)
        
        return detected
    
    def has_markdown_table(self, text: str) -> bool:
        """Check if text contains Markdown table formatting."""
        lines = text.split('\n')
        table_lines = [l for l in lines if '|' in l]
        return len(table_lines) >= 3  # Header + separator + at least 1 row
    
    def has_numeric_data(self, text: str) -> bool:
        """Check if text contains significant numeric data."""
        # Look for patterns like amounts, percentages, rates
        numeric_patterns = [
            r'\d+[.,]\d+\s*€',  # Euro amounts
            r'\d+[.,]\d+\s*%',  # Percentages
            r'\d+[.,]\d{3}',    # Large numbers with thousand separators
        ]
        return any(re.search(pattern, text) for pattern in numeric_patterns)
    
    def is_diagram_reference(self, text: str) -> bool:
        """Check if chunk references a diagram or flowchart."""
        diagram_keywords = [
            'gráfico', 'diagrama', 'esquema', 'flujo',
            'figura', 'ilustración', 'gráfica'
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in diagram_keywords)


async def analyze_documents():
    print("=" * 70)
    print("ANÁLISIS DE TABLAS Y DIAGRAMAS EN DOCUMENTOS")
    print("=" * 70)
    print()
    
    db = TursoClient()
    await db.connect()
    
    detector = TableDetector()
    
    # Get all documents
    docs_result = await db.execute("""
        SELECT id, filename, total_pages 
        FROM documents 
        ORDER BY filename
    """)
    
    print(f"📚 Analizando {len(docs_result.rows)} documentos...\n")
    
    # Stats per document
    doc_stats = {}
    
    for doc in docs_result.rows:
        doc_id = doc['id']
        filename = doc['filename']
        
        # Get chunks for this document
        chunks_result = await db.execute("""
            SELECT content, page_number 
            FROM document_chunks 
            WHERE document_id = ?
        """, [doc_id])
        
        # Analyze chunks
        stats = {
            'total_chunks': len(chunks_result.rows),
            'chunks_with_tables': 0,
            'chunks_with_numeric_data': 0,
            'diagram_references': 0,
            'table_types': defaultdict(int),
            'sample_tables': []
        }
        
        for chunk in chunks_result.rows:
            content = chunk['content']
            page = chunk['page_number']
            
            # Check for tables
            has_table = detector.has_markdown_table(content)
            has_numbers = detector.has_numeric_data(content)
            has_diagram = detector.is_diagram_reference(content)
            
            if has_table:
                stats['chunks_with_tables'] += 1
                
                # Detect table type
                table_types = detector.detect_table_type(content)
                for ttype in table_types:
                    stats['table_types'][ttype] += 1
                
                # Save sample if it's a tax scale
                if 'escala_irpf' in table_types and len(stats['sample_tables']) < 2:
                    stats['sample_tables'].append({
                        'page': page,
                        'type': 'escala_irpf',
                        'preview': content[:200]
                    })
            
            if has_numbers:
                stats['chunks_with_numeric_data'] += 1
            
            if has_diagram:
                stats['diagram_references'] += 1
        
        doc_stats[filename] = stats
    
    # Generate report
    print("📊 RESULTADOS POR DOCUMENTO")
    print("=" * 70)
    
    total_table_documents = 0
    total_diagram_documents = 0
    
    for filename, stats in sorted(doc_stats.items()):
        has_significant_tables = stats['chunks_with_tables'] > 0
        has_diagrams = stats['diagram_references'] > 0
        
        if has_significant_tables or has_diagrams:
            print(f"\n📄 {filename}")
            print(f"   Chunks totales: {stats['total_chunks']}")
            
            if has_significant_tables:
                total_table_documents += 1
                print(f"   ✅ Chunks con tablas: {stats['chunks_with_tables']}")
                print(f"   📊 Chunks con datos numéricos: {stats['chunks_with_numeric_data']}")
                
                if stats['table_types']:
                    print("   Tipos de tablas detectadas:")
                    for ttype, count in sorted(stats['table_types'].items(), key=lambda x: x[1], reverse=True):
                        print(f"      - {ttype}: {count} chunks")
                
                if stats['sample_tables']:
                    print("   Ejemplos:")
                    for sample in stats['sample_tables']:
                        print(f"      • Página {sample['page']}: {sample['type']}")
            
            if has_diagrams:
                total_diagram_documents += 1
                print(f"   🎨 Referencias a diagramas: {stats['diagram_references']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("RESUMEN GENERAL")
    print("=" * 70)
    print(f"Documentos con tablas estructuradas: {total_table_documents}/{len(docs_result.rows)}")
    print(f"Documentos con diagramas: {total_diagram_documents}/{len(docs_result.rows)}")
    
    # Aggregate table types
    all_table_types = defaultdict(int)
    for stats in doc_stats.values():
        for ttype, count in stats['table_types'].items():
            all_table_types[ttype] += count
    
    if all_table_types:
        print("\nTipos de tablas encontradas (total):")
        for ttype, count in sorted(all_table_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {ttype}: {count} chunks")
    
    # Recommendations
    print("\n" + "=" * 70)
    print("RECOMENDACIONES")
    print("=" * 70)
    
    if all_table_types.get('escala_irpf', 0) > 0:
        print("✅ PRIORIDAD ALTA: Crear tabla SQL para escalas IRPF por CCAA")
        print("   - Estructura: ccaa_irpf_scales (ccaa, year, tramo, base, cuota, tipo)")
        print(f"   - Chunks detectados: {all_table_types['escala_irpf']}")
    
    if all_table_types.get('deducciones', 0) > 0:
        print("\n✅ PRIORIDAD MEDIA: Crear tabla SQL para deducciones")
        print(f"   - Chunks detectados: {all_table_types['deducciones']}")
    
    if all_table_types.get('retenciones', 0) > 0:
        print("\n✅ PRIORIDAD MEDIA: Crear tabla SQL para retenciones")
        print(f"   - Chunks detectados: {all_table_types['retenciones']}")
    
    if all_table_types.get('tipos_iva', 0) > 0:
        print("\n✅ Crear tabla SQL para tipos de IVA")
        print(f"   - Chunks detectados: {all_table_types['tipos_iva']}")
    
    if total_diagram_documents > 0:
        print(f"\n📊 Diagramas detectados en {total_diagram_documents} documentos")
        print("   - Considerar extracción visual con Azure DI")
        print("   - Almacenar como imágenes + descripciones LLM")
    
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(analyze_documents())
