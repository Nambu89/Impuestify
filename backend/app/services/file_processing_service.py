"""
File Processing Service for TaxIA

Handles file uploads, classification, text extraction, and embeddings for Workspaces.
Integrates specialized extractors for invoices and payslips.
"""
import logging
import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import UploadFile

from app.database.turso_client import get_db_client
from app.utils.pdf_extractor import extract_pdf_text, PDFExtractionResult

logger = logging.getLogger(__name__)


class FileProcessingService:
    """Service for processing uploaded workspace files."""

    ACCEPTED_TYPES = {
        "application/pdf": "pdf",
        "image/jpeg": "image",
        "image/png": "image",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel",
        "application/vnd.ms-excel": "excel"
    }

    # Whether to generate embeddings (can be disabled for faster uploads)
    ENABLE_EMBEDDINGS = True

    async def process_file_upload(
        self,
        workspace_id: str,
        file: UploadFile,
        file_type_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an uploaded file: save metadata, extract content, and generate embeddings.

        Args:
            workspace_id: ID of the target workspace
            file: FastAPI UploadFile object
            file_type_hint: Optional hint for file type (nomina, factura, etc.)

        Returns:
            Dictionary with created file metadata
        """
        if file.content_type not in self.ACCEPTED_TYPES:
            raise ValueError(f"File type {file.content_type} not supported")

        file_id = str(uuid.uuid4())

        # Read content
        content = await file.read()
        file_size = len(content)

        # Classify file type
        file_category = file_type_hint or self._classify_file_type(file.filename)

        # Extract text and structured data
        extracted_text = ""
        extracted_data = {}
        processing_status = "pending"

        try:
            if file.content_type == "application/pdf":
                # Use PyMuPDF4LLM for text extraction
                result: PDFExtractionResult = await extract_pdf_text(content, file.filename)

                if result.success:
                    extracted_text = result.markdown_text
                    processing_status = "completed"

                    # Apply specialized extractors based on file type
                    if file_category == "factura":
                        extracted_data = await self._extract_invoice_data(extracted_text)
                    elif file_category == "nomina":
                        extracted_data = await self._extract_payslip_data(extracted_text)
                    elif file_category == "declaracion":
                        extracted_data = self._extract_declaration_data(extracted_text)
                    else:
                        # Basic extraction for other document types
                        extracted_data = {"pages": result.total_pages}

                else:
                    extracted_text = ""
                    processing_status = "error"
                    logger.error(f"PDF extraction failed: {result.error}")

            # TODO: Add Excel/Image handling

        except Exception as e:
            logger.error(f"Error extracting text from {file.filename}: {e}")
            processing_status = "error"

        # Save to Database
        db = await get_db_client()
        now = datetime.utcnow().isoformat()

        await db.execute(
            """
            INSERT INTO workspace_files (
                id, workspace_id, filename, file_type, mime_type,
                file_size, extracted_text, extracted_data, processing_status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                file_id,
                workspace_id,
                file.filename,
                file_category,
                file.content_type,
                file_size,
                extracted_text,
                json.dumps(extracted_data) if isinstance(extracted_data, dict) and extracted_data else None,
                processing_status,
                now
            ]
        )

        # Generate embeddings asynchronously (if enabled and extraction succeeded)
        embedding_status = "skipped"
        if self.ENABLE_EMBEDDINGS and processing_status == "completed" and extracted_text:
            try:
                embedding_result = await self._generate_file_embeddings(
                    db, workspace_id, file_id, extracted_text, file.filename
                )
                embedding_status = "completed" if embedding_result.get('success') else "failed"
            except Exception as e:
                logger.error(f"Embedding generation failed for {file.filename}: {e}")
                embedding_status = "error"

        return {
            "id": file_id,
            "filename": file.filename,
            "file_type": file_category,
            "status": processing_status,
            "size": file_size,
            "extracted_data": extracted_data,
            "embedding_status": embedding_status
        }

    def _classify_file_type(self, filename: str) -> str:
        """Classify file type from filename."""
        lower_name = filename.lower()

        # Payslip patterns
        if any(p in lower_name for p in ["nomina", "nómina", "payslip", "salario"]):
            return "nomina"

        # Invoice patterns
        if any(p in lower_name for p in ["factura", "invoice", "fra", "fact"]):
            return "factura"

        # Tax declaration patterns
        if any(p in lower_name for p in [
            "declaracion", "declaración", "modelo",
            "303", "130", "420", "300",
            "390", "100", "200",
        ]):
            return "declaracion"

        return "otro"

    async def _extract_invoice_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from invoice text."""
        try:
            from app.services.invoice_extractor import get_invoice_extractor

            extractor = get_invoice_extractor()
            data = await extractor.extract_from_text(text)

            # Add summary
            data['summary'] = extractor.generate_summary(data)
            data['vat_breakdown'] = extractor.get_vat_breakdown(data)

            return data

        except Exception as e:
            logger.error(f"Invoice extraction failed: {e}")
            return {"error": str(e)}

    async def _extract_payslip_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from payslip text."""
        try:
            from app.services.payslip_extractor import PayslipExtractor

            extractor = PayslipExtractor()
            data = extractor._parse_payslip_data(text)

            # Add summary
            data['summary'] = extractor.generate_summary(data)
            data['stats'] = extractor.get_extraction_stats(data)

            return data

        except Exception as e:
            logger.error(f"Payslip extraction failed: {e}")
            return {"error": str(e)}

    def _extract_declaration_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from tax declaration text (303/130/420)."""
        try:
            from app.services.declaration_extractor import DeclarationExtractor

            extractor = DeclarationExtractor()
            result = extractor.extract(text)

            if not result.success:
                return {"error": result.error, "type": "declaracion"}

            return {
                "type": "declaracion",
                "modelo": result.modelo,
                "metadata": result.metadata,
                "fields": result.fields,
                "territory": result.territory,
                "confidence": result.confidence,
                "casillas_count": len(result.casillas_raw),
            }

        except Exception as e:
            logger.error(f"Declaration extraction failed: {e}")
            return {"error": str(e), "type": "declaracion"}

    async def _generate_file_embeddings(
        self,
        db,
        workspace_id: str,
        file_id: str,
        text: str,
        filename: str
    ) -> Dict[str, Any]:
        """Generate embeddings for file content."""
        try:
            from app.services.workspace_embedding_service import get_workspace_embedding_service

            service = get_workspace_embedding_service()
            result = await service.embed_workspace_file(
                db, workspace_id, file_id, text, filename
            )

            return result

        except ImportError:
            logger.warning("Embedding service not available")
            return {"success": False, "error": "Service not available"}
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def reprocess_file(self, file_id: str) -> Dict[str, Any]:
        """
        Reprocess an existing file (re-extract and re-embed).

        Args:
            file_id: ID of the file to reprocess

        Returns:
            Updated file metadata
        """
        db = await get_db_client()

        # Get file info
        result = await db.execute(
            "SELECT * FROM workspace_files WHERE id = ?",
            [file_id]
        )

        if not result.rows:
            raise ValueError(f"File {file_id} not found")

        file_info = result.rows[0]

        # If we have extracted text, re-run specialized extractors
        extracted_text = file_info.get('extracted_text', '')
        file_category = file_info.get('file_type', 'otro')
        workspace_id = file_info['workspace_id']

        extracted_data = {}

        if extracted_text:
            if file_category == "factura":
                extracted_data = await self._extract_invoice_data(extracted_text)
            elif file_category == "nomina":
                extracted_data = await self._extract_payslip_data(extracted_text)
            elif file_category == "declaracion":
                extracted_data = self._extract_declaration_data(extracted_text)

        # Update database
        await db.execute(
            """
            UPDATE workspace_files
            SET extracted_data = ?, processing_status = 'completed'
            WHERE id = ?
            """,
            [json.dumps(extracted_data) if isinstance(extracted_data, dict) and extracted_data else None, file_id]
        )

        # Regenerate embeddings
        if self.ENABLE_EMBEDDINGS and extracted_text:
            # Delete old embeddings
            from app.services.workspace_embedding_service import get_workspace_embedding_service
            service = get_workspace_embedding_service()
            await service.delete_file_embeddings(db, file_id)

            # Generate new
            await self._generate_file_embeddings(
                db, workspace_id, file_id, extracted_text, file_info['filename']
            )

        return {
            "id": file_id,
            "status": "reprocessed",
            "extracted_data": extracted_data
        }


# Global instance
file_processing_service = FileProcessingService()
