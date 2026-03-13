"""
API endpoints for notification analysis.

Handles:
- PDF upload and analysis
- User notification history
- Analysis retrieval
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Request
from typing import Optional, List, Dict
import os
import uuid
from datetime import datetime
import json
import logging

from app.agents.notification_agent import get_notification_agent
from app.agents.payslip_agent import get_payslip_agent
from app.auth.jwt_handler import get_current_user, TokenData
from app.auth.subscription_guard import require_active_subscription
from app.database.turso_client import TursoClient
from app.services.conversation_service import ConversationService
from app.services.subscription_service import SubscriptionAccess
from app.security import file_validator, rate_limit_notification
from app.utils.document_detector import DocumentDetector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_db():
	"""Dependency for database client."""
	db = TursoClient()
	try:
		yield db
	finally:
		pass  # Connection is managed asyncio-style


@router.post("/analyze")
@rate_limit_notification()  # DDoS Protection:  10/hour, 2/minute (VERY EXPENSIVE)
async def analyze_notification(
	request: Request,  # Required by SlowAPI
	file: UploadFile = File(...),
	notification_date: Optional[str] = Form(None),
	current_user: TokenData = Depends(get_current_user),
	access: SubscriptionAccess = Depends(require_active_subscription)
):
	"""
	Analyze uploaded AEAT notification PDF.
	
	**Request:**
	- `file`: PDF file (multipart/form-data)
	- `notification_date`: ISO date string (optional, defaults to today)
	
	**Response:**
```json
	{
		"id": "uuid",
		"summary": "User-friendly explanation...",
		"type": "Requerimiento de documentación",
		"deadlines": [
			{
				"description": "10 días hábiles",
				"date": "2024-12-20",
				"days_remaining": 8,
				"is_urgent": true
			}
		],
		"region": {
			"region": "Comunidad de Madrid",
			"province": "Madrid",
			"is_foral": false
		},
		"severity": "high",
		"references": [...]
	}
```
	"""
	# === SECURITY LAYER: File Validation ===
	# Read file content
	content = await file.read()
	
	# Validate filename for path traversal
	filename_valid, filename_errors = file_validator.validate_filename(file.filename)
	if not filename_valid:
		raise HTTPException(
			status_code=400,
			detail={
				"error": "Invalid filename",
				"details": filename_errors
			}
		)
	
	# Comprehensive PDF validation
	validation_result = await file_validator.validate_pdf(
		file_content=content,
		filename=file.filename,
		content_type=file.content_type
	)
	
	if not validation_result.is_valid:
		raise HTTPException(
			status_code=400,
			detail={
				"error": "File validation failed",
				"errors": validation_result.errors,
				"warnings": validation_result.warnings
			}
		)
	
	# Log warnings if any
	if validation_result.warnings:
		logger.warning(f"⚠️ File validation warnings for {file.filename}: {validation_result.warnings}")
	
	logger.info(f"✅ File validated: {file.filename} ({validation_result.file_size / 1024:.2f}KB, hash: {validation_result.file_hash[:16]}...)")
	
	# Save uploaded file temporarily
	temp_dir = "/tmp/taxia_notifications"
	os.makedirs(temp_dir, exist_ok=True)
	
	temp_filename = f"{uuid.uuid4()}_{file.filename}"
	temp_path = os.path.join(temp_dir, temp_filename)
	
	try:
		# Write validated content
		with open(temp_path, "wb") as f:
			f.write(content)
		
		# 🆕 STEP 1: Extract text from PDF for type detection
		logger.info("📄 Extracting text from PDF for type detection...")
		try:
			import pymupdf  # PyMuPDF
			doc = pymupdf.open(temp_path)
			# Extract first 2 pages for classification
			pdf_text = ""
			for page_num in range(min(2, len(doc))):
				page = doc[page_num]
				pdf_text += page.get_text()
			doc.close()
			logger.info(f"✅ Extracted {len(pdf_text)} characters from PDF")
		except Exception as e:
			logger.warning(f"⚠️ Could not extract text for classification: {e}")
			pdf_text = ""  # Fallback to empty
		
		# Validate that we have enough text to classify
		if not pdf_text or len(pdf_text) < 50:
			logger.error("❌ Could not extract enough text from PDF for classification")
			return {
				"needs_clarification": True,
				"message": "No se pudo leer el contenido del PDF. Por favor, indica el tipo de documento:",
				"detection": {"type": "other", "confidence": 0.0, "reasoning": "PDF sin texto extraíble"},
				"options": [
					{"value": "payslip", "label": "Nómina"},
					{"value": "aeat_notification", "label": "Notificación de Hacienda"},
					{"value": "other", "label": "Otro"}
				]
			}
		
		# 🆕 STEP 2: Detect document type
		detector = DocumentDetector()
		detection = await detector.detect_type(pdf_text)
		
		logger.info(f"🔍 Document type: {detection['type']} (confidence: {detection['confidence']})")
		
		# 🆕 STEP 3: Check if we should ask user
		if detector.should_ask_user(detection):
			logger.warning(f"⚠️ Low confidence ({detection['confidence']}), asking user for clarification")
			# Return special response asking user to clarify
			return {
				"needs_clarification": True,
				"message": "No estoy seguro del tipo de documento. ¿Es una nómina o una notificación de Hacienda?",
				"detection": detection,
				"options": [
					{"value": "payslip", "label": "Nómina"},
					{"value": "aeat_notification", "label": "Notificación de Hacienda"},
					{"value": "other", "label": "Otro"}
				]
			}
		
		# 🆕 STEP 4: Route to appropriate agent based on type
		if detection['type'] == 'payslip':
			logger.info("📊 Routing to PayslipAgent...")
			agent = get_payslip_agent()
			analysis = await agent.analyze_payslip(pdf_path=temp_path)
			document_type = "payslip"
		else:  # aeat_notification or other (treat as notification)
			logger.info("📬 Routing to NotificationAgent...")
			agent = get_notification_agent()
			analysis = await agent.analyze_notification(
				pdf_path=temp_path,
				notification_date=notification_date
			)
			document_type = "aeat_notification"
		
		# Store in database
		db = TursoClient()
		await db.connect()
		
		analysis_id = str(uuid.uuid4())
		
		await db.execute(
			"""
			INSERT INTO notification_analyses 
			(id, user_id, filename, file_hash, notification_type, region, is_foral,
			 summary, deadlines, reference_links, severity, notification_date, created_at)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			""",
			[
				analysis_id,
				current_user.user_id,
				file.filename,
				analysis['file_hash'],
				analysis['type'],
				analysis['region'].get('region'),
				1 if analysis['region'].get('is_foral') else 0,
				analysis['summary'],
				json.dumps(analysis['deadlines']),
				json.dumps(analysis.get('reference_links', analysis.get('references', []))),
				analysis['severity'],
				analysis['notification_date'],
				datetime.now().isoformat()
			]
		)
		
		# Create conversation for this notification
		conv_service = ConversationService(db)
		conversation = await conv_service.create_conversation(
			user_id=current_user.user_id,
			title=f"Notificación: {analysis['type']}"
		)
		conversation_id = conversation["id"]
		
		# Format notification in friendly language
		analysis_content = format_notification_friendly(
			notification_type=analysis['type'],
			summary=analysis['summary'],
			deadlines=analysis['deadlines'],
			region=analysis['region'],
			severity=analysis['severity']
		)
		
		# Save analysis as assistant message in conversation
		await conv_service.add_message(
			conversation_id=conversation_id,
			role="assistant",
			content=analysis_content,
			metadata={
				"notification_id": analysis_id,
				"notification_type": analysis['type'],
				"region": analysis['region'].get('region'),
				"deadlines": analysis['deadlines']
			}
		)
		
		await db.disconnect()
		
		# Return analysis with ID and conversation_id
		return {
			"id": analysis_id,
			"conversation_id": conversation_id,
			**analysis
		}
	
	except Exception as e:
		raise HTTPException(
			status_code=500,
			detail=f"Analysis failed: {str(e)}"
		)
	
	finally:
		# Cleanup temp file
		if os.path.exists(temp_path):
			os.remove(temp_path)


@router.get("/history")
async def get_notification_history(
	current_user: TokenData = Depends(get_current_user),
	limit: int = 10
):
	"""
	Get user's notification analysis history.
	
	**Query params:**
	- `limit`: Max number of records (default: 10)
	
	**Response:**
```json
	[
		{
			"id": "uuid",
			"filename": "notificacion.pdf",
			"type": "Requerimiento",
			"severity": "high",
			"notification_date": "2024-12-10",
			"created_at": "2024-12-10T10:30:00"
		}
	]
```
	"""
	db = TursoClient()
	await db.connect()
	
	try:
		result = await db.execute(
			"""
			SELECT 
				id, filename, notification_type, severity,
				notification_date, created_at
			FROM notification_analyses
			WHERE user_id = ?
			ORDER BY created_at DESC
			LIMIT ?
			""",
			[current_user.user_id, limit]
		)
		
		history = []
		for row in result.rows:
			history.append({
				'id': row['id'],
				'filename': row['filename'],
				'type': row['notification_type'],
				'severity': row['severity'],
				'notification_date': row['notification_date'],
				'created_at': row['created_at']
			})
		
		return history
	
	finally:
		await db.disconnect()


@router.get("/{analysis_id}")
async def get_notification_analysis(
	analysis_id: str,
	current_user: TokenData = Depends(get_current_user)
):
	"""
	Get specific notification analysis.
	
	**Path params:**
	- `analysis_id`: UUID of analysis
	
	**Response:**
	Full analysis object
	"""
	db = TursoClient()
	await db.connect()
	
	try:
		result = await db.execute(
			"""
			SELECT * FROM notification_analyses
			WHERE id = ? AND user_id = ?
			""",
			[analysis_id, current_user.user_id]
		)
		
		if not result.rows:
			raise HTTPException(status_code=404, detail="Analysis not found")
		
		row = result.rows[0]
		
		return {
			'id': row['id'],
			'filename': row['filename'],
			'type': row['notification_type'],
			'summary': row['summary'],
			'deadlines': json.loads(row['deadlines']) if row['deadlines'] else [],
			'region': {
				'region': row['region'],
				'is_foral': bool(row['is_foral'])
			},
			'reference_links': json.loads(row['reference_links']) if row['reference_links'] else [],
			'severity': row['severity'],
			'notification_date': row['notification_date'],
			'created_at': row['created_at']
		}
	
	finally:
		await db.disconnect()


@router.delete("/{analysis_id}")
async def delete_notification_analysis(
	analysis_id: str,
	current_user: TokenData = Depends(get_current_user)
):
	"""
	Delete notification analysis.
	
	**Path params:**
	- `analysis_id`: UUID of analysis
	"""
	db = TursoClient()
	await db.connect()
	
	try:
		# Verify ownership
		result = await db.execute(
			"SELECT id FROM notification_analyses WHERE id = ? AND user_id = ?",
			[analysis_id, current_user.user_id]
		)
		
		if not result.rows:
			raise HTTPException(status_code=404, detail="Analysis not found")
		
		# Delete
		await db.execute(
			"DELETE FROM notification_analyses WHERE id = ?",
			[analysis_id]
		)
		
		return {"message": "Analysis deleted successfully"}
	
	finally:
		await db.disconnect()


def format_notification_friendly(
	notification_type: str,
	summary: str,
	deadlines: List[Dict],
	region: Dict,
	severity: str
) -> str:
	"""
	Wrap the LLM summary with structured deadline data.

	The LLM already produces an answer-first response. This function only adds:
	- A structured deadlines block (calculated server-side, more reliable than LLM)
	- A "questions?" prompt at the end

	Args:
		notification_type: Type detected by agent (e.g., "Providencia de apremio")
		summary: Agent's summary text (answer-first format)
		deadlines: List of deadline dicts with pre-calculated dates
		region: Region info dict
		severity: Severity level (low/medium/high/critical)

	Returns:
		Formatted message
	"""
	parts = [summary]

	# Append structured deadlines block only if deadlines exist and are not already
	# mentioned in the summary (the LLM may have included them)
	if deadlines:
		deadline_lines = []
		for deadline in deadlines:
			desc = deadline.get('description', 'Plazo')
			date = deadline.get('date')
			days = deadline.get('days_remaining')
			urgent = deadline.get('is_urgent', False)

			urgency_emoji = "🔴" if urgent else "📅"

			if date and days is not None:
				if days < 0:
					deadline_lines.append(f"{urgency_emoji} **{desc}**: vencido (hace {abs(days)} días)")
				elif days == 0:
					deadline_lines.append(f"{urgency_emoji} **{desc}**: **HOY es el último día**")
				elif days <= 3:
					deadline_lines.append(f"{urgency_emoji} **{desc}**: {date} (quedan {days} días)")
				else:
					deadline_lines.append(f"{urgency_emoji} **{desc}**: {date} ({days} días)")
			else:
				deadline_lines.append(f"{urgency_emoji} **{desc}**")

		if deadline_lines:
			parts.append("\n\n**Plazos calculados:**\n" + "\n".join(deadline_lines))

	parts.append("\n\n---\n¿Tienes dudas? Pregúntame lo que no entiendas.")

	return "".join(parts)