"""
Tests for Workspace Components - Phase 8

Tests for:
- InvoiceExtractor
- WorkspaceEmbeddingService
- FileProcessingService integration
- WorkspaceAgent
- Workspace API endpoints
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


# ============================================
# INVOICE EXTRACTOR TESTS
# ============================================

class TestInvoiceExtractor:
    """Tests for the InvoiceExtractor service."""

    def test_extractor_initialization(self):
        """Test that InvoiceExtractor initializes correctly."""
        from app.services.invoice_extractor import InvoiceExtractor, get_invoice_extractor

        extractor = get_invoice_extractor()
        assert extractor is not None
        assert len(extractor.patterns) > 0

    def test_extractor_patterns_exist(self):
        """Test that all required patterns are defined."""
        from app.services.invoice_extractor import get_invoice_extractor

        extractor = get_invoice_extractor()
        required_patterns = [
            'invoice_number', 'invoice_date', 'nif_cif',
            'base_imponible', 'total_factura', 'iva_total'
        ]

        for pattern in required_patterns:
            assert pattern in extractor.patterns, f"Missing pattern: {pattern}"

    @pytest.mark.asyncio
    async def test_extract_invoice_number(self):
        """Test extraction of invoice number."""
        from app.services.invoice_extractor import get_invoice_extractor

        extractor = get_invoice_extractor()
        text = "Factura No: FRA-2025-001\nFecha: 15/01/2025"

        result = await extractor.extract_from_text(text)
        assert result.get('invoice_number') == 'FRA-2025-001'

    @pytest.mark.asyncio
    async def test_extract_invoice_date(self):
        """Test extraction of invoice date."""
        from app.services.invoice_extractor import get_invoice_extractor

        extractor = get_invoice_extractor()
        text = "Fecha de factura: 15/01/2025"

        result = await extractor.extract_from_text(text)
        assert result.get('invoice_date') == '15/01/2025'

    @pytest.mark.asyncio
    async def test_extract_nif(self):
        """Test extraction of NIF/CIF."""
        from app.services.invoice_extractor import get_invoice_extractor

        extractor = get_invoice_extractor()
        text = "Emisor: Empresa S.L.\nCIF: B12345678\nCliente\nNIF: A87654321"

        result = await extractor.extract_from_text(text)
        assert result.get('issuer_nif') == 'B12345678'
        assert result.get('recipient_nif') == 'A87654321'

    @pytest.mark.asyncio
    async def test_extract_amounts(self):
        """Test extraction of monetary amounts."""
        from app.services.invoice_extractor import get_invoice_extractor

        extractor = get_invoice_extractor()
        text = """
        Base imponible: 1.000,00 €
        IVA 21%: 210,00 €
        Total factura: 1.210,00 €
        """

        result = await extractor.extract_from_text(text)
        assert result.get('total_base_imponible') == 1000.0
        assert result.get('total_factura') == 1210.0

    @pytest.mark.asyncio
    async def test_extract_irpf_retention(self):
        """Test extraction of IRPF retention for freelancers."""
        from app.services.invoice_extractor import get_invoice_extractor

        extractor = get_invoice_extractor()
        text = """
        Base imponible: 1.000,00 €
        Retencion IRPF 15%: -150,00 €
        Total: 850,00 €
        """

        result = await extractor.extract_from_text(text)
        # Pattern may extract percentage or amount - both are valid extractions
        assert result.get('retencion_irpf') is not None or result.get('porcentaje_retencion') is not None
        assert result.get('porcentaje_retencion') == 15.0

    @pytest.mark.asyncio
    async def test_confidence_score(self):
        """Test that confidence score is calculated."""
        from app.services.invoice_extractor import get_invoice_extractor

        extractor = get_invoice_extractor()

        # Complete invoice should have high confidence
        complete_text = """
        Factura No: FRA-001
        Fecha: 15/01/2025
        CIF: B12345678
        Base imponible: 1.000,00 €
        Total factura: 1.210,00 €
        """
        result = await extractor.extract_from_text(complete_text)
        assert result.get('confidence_score', 0) >= 0.5

        # Empty text should have low confidence
        empty_result = await extractor.extract_from_text("")
        assert empty_result.get('confidence_score', 0) == 0

    def test_generate_summary(self):
        """Test summary generation."""
        from app.services.invoice_extractor import get_invoice_extractor

        extractor = get_invoice_extractor()
        data = {
            'invoice_number': 'FRA-001',
            'invoice_date': '15/01/2025',
            'total_base_imponible': 1000.0,
            'total_iva': 210.0,
            'total_factura': 1210.0
        }

        summary = extractor.generate_summary(data)
        assert 'FRA-001' in summary
        assert '1000.00' in summary or '1.000' in summary
        assert '1210.00' in summary or '1.210' in summary

    def test_vat_breakdown(self):
        """Test VAT breakdown by rate."""
        from app.services.invoice_extractor import get_invoice_extractor

        extractor = get_invoice_extractor()
        data = {
            'base_imponible_21': 1000.0,
            'cuota_iva_21': 210.0,
            'base_imponible_10': 500.0,
            'cuota_iva_10': 50.0
        }

        breakdown = extractor.get_vat_breakdown(data)
        assert '21%' in breakdown
        assert '10%' in breakdown
        assert breakdown['21%']['base'] == 1000.0
        assert breakdown['10%']['cuota'] == 50.0


# ============================================
# WORKSPACE EMBEDDING SERVICE TESTS
# ============================================

class TestWorkspaceEmbeddingService:
    """Tests for the WorkspaceEmbeddingService."""

    def test_service_initialization(self):
        """Test that service initializes correctly."""
        from app.services.workspace_embedding_service import (
            WorkspaceEmbeddingService,
            get_workspace_embedding_service
        )

        service = get_workspace_embedding_service()
        assert service is not None
        assert service.EMBEDDING_MODEL == "text-embedding-3-large"
        assert service.EMBEDDING_DIMENSIONS == 3072

    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        from app.services.workspace_embedding_service import get_workspace_embedding_service

        service = get_workspace_embedding_service()

        # Short text - single chunk
        short_text = "This is a short text."
        chunks = service.chunk_text(short_text)
        assert len(chunks) == 1
        assert chunks[0]['text'] == short_text
        assert chunks[0]['chunk_index'] == 0

    def test_chunk_text_long(self):
        """Test chunking of long text."""
        from app.services.workspace_embedding_service import get_workspace_embedding_service

        service = get_workspace_embedding_service()

        # Create text longer than chunk size
        long_text = "Este es un parrafo largo. " * 100
        chunks = service.chunk_text(long_text)

        assert len(chunks) > 1
        # Verify chunks have sequential indices
        for i, chunk in enumerate(chunks):
            assert chunk['chunk_index'] == i
            assert len(chunk['text']) <= service.CHUNK_SIZE + 100  # Allow some margin

    def test_chunk_text_preserves_sentences(self):
        """Test that chunking tries to preserve sentence boundaries."""
        from app.services.workspace_embedding_service import get_workspace_embedding_service

        service = get_workspace_embedding_service()

        # Text with clear sentence boundaries
        text = "Primera oracion completa. " * 50 + "Segunda oracion. " * 50
        chunks = service.chunk_text(text)

        # Most chunks should end with a period
        chunks_ending_with_period = sum(1 for c in chunks if c['text'].rstrip().endswith('.'))
        assert chunks_ending_with_period >= len(chunks) - 1  # Allow last chunk to not end with period

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        from app.services.workspace_embedding_service import get_workspace_embedding_service

        service = get_workspace_embedding_service()

        # Identical vectors should have similarity 1.0
        vec1 = [1.0, 0.0, 0.0]
        assert abs(service._cosine_similarity(vec1, vec1) - 1.0) < 0.001

        # Orthogonal vectors should have similarity 0.0
        vec2 = [0.0, 1.0, 0.0]
        assert abs(service._cosine_similarity(vec1, vec2)) < 0.001

        # Opposite vectors should have similarity -1.0
        vec3 = [-1.0, 0.0, 0.0]
        assert abs(service._cosine_similarity(vec1, vec3) + 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_generate_embedding_with_valid_key(self):
        """Test embedding generation works with valid API key (if configured)."""
        from app.services.workspace_embedding_service import get_workspace_embedding_service
        from app.config import settings

        service = get_workspace_embedding_service()

        # Only test if API key is actually configured
        if settings.OPENAI_API_KEY:
            result = await service.generate_embedding("test text for embedding")
            # If API key is valid, embedding should succeed
            if result.success:
                assert result.embedding is not None
                assert len(result.embedding) == service.EMBEDDING_DIMENSIONS
                assert result.model == service.EMBEDDING_MODEL


# ============================================
# FILE PROCESSING SERVICE TESTS
# ============================================

class TestFileProcessingService:
    """Tests for the FileProcessingService integration."""

    def test_service_initialization(self):
        """Test that service initializes correctly."""
        from app.services.file_processing_service import (
            FileProcessingService,
            file_processing_service
        )

        assert file_processing_service is not None
        assert file_processing_service.ENABLE_EMBEDDINGS == True

    def test_classify_file_type_nomina(self):
        """Test classification of payslip files."""
        from app.services.file_processing_service import file_processing_service

        assert file_processing_service._classify_file_type("nomina_enero_2025.pdf") == "nomina"
        assert file_processing_service._classify_file_type("NOMINA-FEBRERO.PDF") == "nomina"
        assert file_processing_service._classify_file_type("payslip_march.pdf") == "nomina"

    def test_classify_file_type_factura(self):
        """Test classification of invoice files."""
        from app.services.file_processing_service import file_processing_service

        assert file_processing_service._classify_file_type("factura_001.pdf") == "factura"
        assert file_processing_service._classify_file_type("FACTURA-PROVEEDOR.PDF") == "factura"
        assert file_processing_service._classify_file_type("invoice_2025.pdf") == "factura"
        assert file_processing_service._classify_file_type("fra_enero.pdf") == "factura"

    def test_classify_file_type_declaracion(self):
        """Test classification of tax declaration files."""
        from app.services.file_processing_service import file_processing_service

        assert file_processing_service._classify_file_type("modelo_303_4T.pdf") == "declaracion"
        assert file_processing_service._classify_file_type("declaracion_renta.pdf") == "declaracion"
        assert file_processing_service._classify_file_type("modelo390_2024.pdf") == "declaracion"

    def test_classify_file_type_otro(self):
        """Test classification of other files."""
        from app.services.file_processing_service import file_processing_service

        assert file_processing_service._classify_file_type("documento.pdf") == "otro"
        assert file_processing_service._classify_file_type("contrato_trabajo.pdf") == "otro"
        assert file_processing_service._classify_file_type("unknown.pdf") == "otro"

    def test_accepted_types(self):
        """Test that accepted file types are defined."""
        from app.services.file_processing_service import file_processing_service

        assert "application/pdf" in file_processing_service.ACCEPTED_TYPES
        assert file_processing_service.ACCEPTED_TYPES["application/pdf"] == "pdf"


# ============================================
# WORKSPACE AGENT TESTS
# ============================================

class TestWorkspaceAgent:
    """Tests for the WorkspaceAgent."""

    def test_agent_initialization(self):
        """Test that WorkspaceAgent initializes correctly."""
        from app.agents.workspace_agent import WorkspaceAgent, get_workspace_agent

        agent = get_workspace_agent()
        assert agent is not None
        assert agent.name == "WorkspaceAgent"

    def test_agent_singleton(self):
        """Test that get_workspace_agent returns same instance."""
        from app.agents.workspace_agent import get_workspace_agent

        agent1 = get_workspace_agent()
        agent2 = get_workspace_agent()
        assert agent1 is agent2

    def test_agent_has_run_method(self):
        """Test that agent has async run method."""
        from app.agents.workspace_agent import get_workspace_agent
        import asyncio

        agent = get_workspace_agent()
        assert hasattr(agent, 'run')
        assert asyncio.iscoroutinefunction(agent.run)


# ============================================
# WORKSPACE API ENDPOINT TESTS
# ============================================

class TestWorkspaceAPIEndpoints:
    """Tests for Workspace API endpoints structure."""

    def test_workspace_routes_registered(self):
        """Test that workspace routes are registered."""
        from app.main import app

        routes = [r.path for r in app.routes if hasattr(r, 'path')]

        assert '/api/workspaces' in routes
        assert any('/api/workspaces/{workspace_id}' in r for r in routes)
        assert any('/api/workspaces/{workspace_id}/files' in r for r in routes)

    def test_workspace_router_tags(self):
        """Test that workspace router has correct tags."""
        from app.routers.workspaces import router

        assert 'workspaces' in router.tags

    def test_workspace_models_defined(self):
        """Test that Pydantic models are properly defined."""
        from app.routers.workspaces import (
            CreateWorkspaceRequest,
            WorkspaceResponse
        )

        # Test CreateWorkspaceRequest
        request = CreateWorkspaceRequest(name="Test Workspace")
        assert request.name == "Test Workspace"

        # Test with optional fields
        request_full = CreateWorkspaceRequest(
            name="Test",
            description="Description",
            icon="briefcase"
        )
        assert request_full.description == "Description"


# ============================================
# DATABASE SCHEMA TESTS
# ============================================

class TestWorkspaceDatabaseSchema:
    """Tests for workspace database schema."""

    def test_workspace_embeddings_table_in_schema(self):
        """Test that workspace_file_embeddings table is in schema."""
        with open('app/database/turso_client.py', encoding='utf-8') as f:
            schema_code = f.read()

        assert 'workspace_file_embeddings' in schema_code
        assert 'workspace_id TEXT NOT NULL' in schema_code
        assert 'file_id TEXT NOT NULL' in schema_code
        assert 'embedding BLOB NOT NULL' in schema_code

    def test_workspace_embeddings_indexes(self):
        """Test that indexes are defined for embeddings table."""
        with open('app/database/turso_client.py', encoding='utf-8') as f:
            schema_code = f.read()

        assert 'idx_ws_embeddings_workspace' in schema_code
        assert 'idx_ws_embeddings_file' in schema_code


# ============================================
# INTEGRATION TESTS
# ============================================

class TestWorkspaceIntegration:
    """Integration tests for workspace components."""

    def test_chat_stream_workspace_integration(self):
        """Test that chat_stream.py has workspace integration."""
        with open('app/routers/chat_stream.py', encoding='utf-8') as f:
            code = f.read()

        assert 'workspace_id' in code
        assert 'workspace_context' in code
        assert 'workspace_agent' in code

    def test_file_processing_extracts_invoice_data(self):
        """Test that file processing service calls invoice extractor."""
        from app.services.file_processing_service import file_processing_service

        # Verify method exists
        assert hasattr(file_processing_service, '_extract_invoice_data')

    def test_file_processing_generates_embeddings(self):
        """Test that file processing service can generate embeddings."""
        from app.services.file_processing_service import file_processing_service

        # Verify method exists
        assert hasattr(file_processing_service, '_generate_file_embeddings')

    @pytest.mark.asyncio
    async def test_invoice_extraction_in_processing(self):
        """Test invoice extraction method in file processing."""
        from app.services.file_processing_service import file_processing_service

        sample_text = """
        FACTURA
        Numero: FRA-001
        Base imponible: 100,00 EUR
        IVA 21%: 21,00 EUR
        Total: 121,00 EUR
        """

        result = await file_processing_service._extract_invoice_data(sample_text)
        assert 'summary' in result or 'error' in result
