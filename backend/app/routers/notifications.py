"""
API endpoints for notification analysis.

Handles:
- PDF upload and analysis
- User notification history
- Analysis retrieval
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Request
from typing import Optional, List
import os
import uuid
from datetime import datetime
import json
import logging

from app.agents.notification_agent import get_notification_agent
from app.auth.jwt_handler import get_current_user
from app.database.turso_client import TursoClient
from app.services.conversation_service import ConversationService
from app.security import file_validator, rate_limit_notification

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
	current_user = Depends(get_current_user)
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
		
		# Analyze with agent
		agent = get_notification_agent()
		analysis = await agent.analyze_notification(
			pdf_path=temp_path,
			notification_date=notification_date
		)
		
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
		
		# Save analysis as assistant message in conversation
		analysis_content = f"""📋 **Análisis de Notificación: {analysis['type']}**

{analysis['summary']}

---

💡 Puedes hacerme preguntas sobre esta notificación y te ayudaré con toda la información de la AEAT."""
		
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
	current_user = Depends(get_current_user),
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
	current_user = Depends(get_current_user)
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
	current_user = Depends(get_current_user)
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