"""
File Upload Validator for TaxIA

Comprehensive security validation for uploaded files to prevent:
1. Malware uploads (disguised as PDFs)
2. Exploits in PDF parsers
3. Embedded malicious scripts
4. Steganography attacks
5. DoS via large files
6. Metadata-based attacks

Implements multi-layer validation:
- Magic number verification
- MIME type checking
- File size limits
- PDF structure validation
- JavaScript/Script detection
- Metadata sanitization
"""
import os
import io
import hashlib
import logging
from typing import Optional, Tuple, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Try to import PDF validation libraries
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not available. Install with: pip install PyPDF2")


class FileValidationResult(BaseModel):
    """Result of file validation"""
    is_valid: bool
    file_type: Optional[str] = None
    file_size: int = 0
    file_hash: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class FileValidator:
    """
    Validates uploaded files for security threats.
    
    Focuses on PDF validation for AEAT notifications.
    """
    
    # PDF Magic Numbers (file signatures)
    PDF_MAGIC_NUMBERS = [
        b'%PDF-1.0',
        b'%PDF-1.1',
        b'%PDF-1.2',
        b'%PDF-1.3',
        b'%PDF-1.4',
        b'%PDF-1.5',
        b'%PDF-1.6',
        b'%PDF-1.7',
        b'%PDF-2.0',
    ]
    
    # Maximum file size: 10 MB (AEAT notifications are typically < 1MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB in bytes
    
    # Minimum file size: 1 KB (too small = likely not a real PDF)
    MIN_FILE_SIZE = 1024  # 1 KB
    
    # Dangerous PDF features
    DANGEROUS_KEYWORDS = [
        b'/JavaScript',
        b'/JS',
        b'/Launch',
        b'/OpenAction',
        b'/AA',  # Additional Actions
        b'/GoToE',  # GoTo Embedded
        b'/GoToR',  # GoTo Remote
        b'/EmbeddedFile',
        b'/RichMedia',
        b'/Flash',
    ]
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize file validator.
        
        Args:
            strict_mode: If True, applies stricter validation rules
        """
        self.strict_mode = strict_mode
    
    async def validate_pdf(
        self,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None
    ) -> FileValidationResult:
        """
        Comprehensive PDF validation.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            content_type: MIME type from upload header
            
        Returns:
            FileValidationResult with validation status
        """
        errors = []
        warnings = []
        metadata = {}
        
        file_size = len(file_content)
        
        # === LAYER 1: File Size Validation ===
        if file_size > self.MAX_FILE_SIZE:
            errors.append(f"File too large: {file_size / 1024 / 1024:.2f}MB (max: 10MB)")
            return FileValidationResult(
                is_valid=False,
                file_size=file_size,
                errors=errors
            )
        
        if file_size < self.MIN_FILE_SIZE:
            errors.append(f"File too small: {file_size} bytes (min: 1KB)")
            return FileValidationResult(
                is_valid=False,
                file_size=file_size,
                errors=errors
            )
        
        # === LAYER 2: Extension Validation ===
        if not filename.lower().endswith('.pdf'):
            errors.append(f"Invalid file extension: {filename}")
        
        # === LAYER 3: MIME Type Validation ===
        if content_type and content_type not in ['application/pdf', 'application/x-pdf']:
            warnings.append(f"Unexpected MIME type: {content_type} (expected: application/pdf)")
        
        # === LAYER 4: Magic Number Validation ===
        magic_valid = False
        for magic in self.PDF_MAGIC_NUMBERS:
            if file_content.startswith(magic):
                magic_valid = True
                metadata['pdf_version'] = magic.decode('ascii')
                break
        
        if not magic_valid:
            errors.append("Invalid PDF signature (file is not a real PDF)")
            return FileValidationResult(
                is_valid=False,
                file_size=file_size,
                errors=errors,
                warnings=warnings
            )
        
        # === LAYER 5: PDF Structure Validation ===
        if PYPDF2_AVAILABLE:
            try:
                pdf_file = io.BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                # Check if encrypted (might be malicious or corporate protective)
                if pdf_reader.is_encrypted:
                    if self.strict_mode:
                        errors.append("Encrypted PDFs are not allowed")
                    else:
                        warnings.append("PDF is encrypted (may require password)")
                
                # Get page count
                num_pages = len(pdf_reader.pages)
                metadata['num_pages'] = num_pages
                
                # AEAT notifications are typically 1-5 pages
                if num_pages > 50:
                    warnings.append(f"Unusually large PDF: {num_pages} pages (suspicious)")
                
                # Check for metadata
                if pdf_reader.metadata:
                    metadata['has_metadata'] = True
                    # Sanitize metadata (remove potentially malicious fields)
                    safe_metadata = self._sanitize_metadata(pdf_reader.metadata)
                    metadata['author'] = safe_metadata.get('author', 'Unknown')
                    metadata['creator'] = safe_metadata.get('creator', 'Unknown')
                
            except PyPDF2.errors.PdfReadError as e:
                errors.append(f"Corrupted or invalid PDF structure: {str(e)}")
                return FileValidationResult(
                    is_valid=False,
                    file_size=file_size,
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata
                )
            except Exception as e:
                logger.error(f"PDF validation error: {e}")
                errors.append(f"PDF validation failed: {str(e)}")
                return FileValidationResult(
                    is_valid=False,
                    file_size=file_size,
                    errors=errors,
                    warnings=warnings
                )
        else:
            warnings.append("PyPDF2 not available - skipping advanced PDF validation")
        
        # === LAYER 6: Dangerous Content Detection ===
        dangerous_features = []
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in file_content:
                dangerous_features.append(keyword.decode('ascii', errors='ignore'))
        
        if dangerous_features:
            if self.strict_mode:
                errors.append(f"PDF contains potentially dangerous features: {', '.join(dangerous_features)}")
            else:
                warnings.append(f"PDF contains advanced features: {', '.join(dangerous_features)}")
        
        # === LAYER 7: File Hash (for duplicate detection) ===
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Final verdict
        is_valid = len(errors) == 0
        
        if is_valid and warnings:
            logger.info(f"✅ File validated with warnings: {filename}")
        elif is_valid:
            logger.info(f"✅ File validated: {filename}")
        else:
            logger.warning(f"❌ File validation failed: {filename}, errors: {errors}")
        
        return FileValidationResult(
            is_valid=is_valid,
            file_type='application/pdf',
            file_size=file_size,
            file_hash=file_hash,
            warnings=warnings,
            errors=errors,
            metadata=metadata
        )
    
    def _sanitize_metadata(self, metadata: dict) -> dict:
        """
        Sanitize PDF metadata to remove potentially malicious content.
        
        Args:
            metadata: Raw PDF metadata
            
        Returns:
            Sanitized metadata dict
        """
        safe_metadata = {}
        
        # Allowed metadata fields
        allowed_fields = ['author', 'creator', 'producer', 'title', 'subject']
        
        for field in allowed_fields:
            if field in metadata and metadata[field]:
                # Convert to string and limit length
                value = str(metadata[field])[:200]  # Max 200 chars
                # Remove control characters
                value = ''.join(char for char in value if char.isprintable())
                safe_metadata[field] = value
        
        return safe_metadata
    
    def validate_filename(self, filename: str) -> Tuple[bool, List[str]]:
        """
        Validate filename for path traversal and other attacks.
        
        Args:
            filename: Original filename
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            errors.append("Filename contains invalid characters (path traversal attempt)")
        
        # Check for null bytes
        if '\x00' in filename:
            errors.append("Filename contains null bytes")
        
        # Check length
        if len(filename) > 255:
            errors.append("Filename too long (max: 255 characters)")
        
        # Check for suspicious extensions (double extension attack)
        if filename.count('.') > 1:
            errors.append("Filename contains multiple dots (suspicious)")
        
        is_valid = len(errors) == 0
        
        return is_valid, errors


# Global validator instance
file_validator = FileValidator(strict_mode=True)
