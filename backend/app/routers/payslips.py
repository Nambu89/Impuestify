"""
Payslips router - Endpoints para gestión de nóminas
"""
import os
import uuid
import json
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.database.models import Payslip, PayslipCreate
from app.database.turso_client import get_db_client
from app.services.payslip_extractor import PayslipExtractor
from app.agents.payslip_agent import get_payslip_agent
from app.auth.jwt_handler import get_current_user
from app.auth.subscription_guard import require_active_subscription
from app.services.subscription_service import SubscriptionAccess

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payslips", tags=["payslips"])


@router.post("/upload", response_model=Payslip)
async def upload_payslip(
	file: UploadFile = File(...),
	current_user: dict = Depends(get_current_user),
	access: SubscriptionAccess = Depends(require_active_subscription)
):
	"""
	Sube y procesa una nómina en PDF.
	
	Args:
		file: Archivo PDF de la nómina
		current_user: Usuario autenticado
		
	Returns:
		Payslip: Nómina procesada con datos extraídos
	"""
	try:
		user_id = current_user.user_id
		
		# Validar que sea un PDF
		if not file.filename.endswith('.pdf'):
			raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")
		
		# Crear directorio de uploads si no existe
		upload_dir = "/tmp/payslips"
		os.makedirs(upload_dir, exist_ok=True)
		
		# Guardar archivo temporalmente
		file_path = os.path.join(upload_dir, f"{user_id}_{file.filename}")
		with open(file_path, "wb") as f:
			content = await file.read()
			f.write(content)
		
		file_size = len(content)
		
		# Extraer datos con PayslipExtractor
		extractor = PayslipExtractor()
		extracted_data = await extractor.extract_from_pdf(file_path)
		
		# Generar ID único
		payslip_id = str(uuid.uuid4())
		
		if extracted_data.get("extraction_status") == "failed":
			# Guardar en BD como fallida
			extraction_status = "failed"
			extracted_data_json = json.dumps({"error": extracted_data.get("error", "Unknown error")})
			summary = "Error en la extracción"
			period_month = None
			period_year = None
			company_name = None
			employee_name = None
			employee_nif = None
			gross_salary = None
			net_salary = None
			irpf_withholding = None
			irpf_percentage = None
			ss_contribution = None
		else:
			# Generar resumen
			summary = extractor.generate_summary(extracted_data)
			extraction_status = "completed"
			extracted_data_json = json.dumps(extracted_data)
			period_month = extracted_data.get("period_month")
			period_year = extracted_data.get("period_year")
			company_name = extracted_data.get("company_name")
			employee_name = extracted_data.get("employee_name")
			employee_nif = extracted_data.get("employee_nif")
			gross_salary = extracted_data.get("gross_salary")
			net_salary = extracted_data.get("net_salary")
			irpf_withholding = extracted_data.get("irpf_amount")
			irpf_percentage = extracted_data.get("irpf_percentage")
			ss_contribution = extracted_data.get("ss_contribution")
		
		# Guardar en base de datos
		db = await get_db_client()
		await db.execute("""
			INSERT INTO payslips (
				id, user_id, filename, file_path, file_size,
				period_month, period_year, company_name, employee_name, employee_nif,
				gross_salary, net_salary, irpf_withholding, irpf_percentage, ss_contribution,
				extraction_status, extracted_data, analysis_summary
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		""", [
			payslip_id, user_id, file.filename,
			file_path, file_size,
			period_month, period_year,
			company_name, employee_name, employee_nif,
			gross_salary, net_salary,
			irpf_withholding, irpf_percentage, ss_contribution,
			extraction_status, extracted_data_json, summary
		])
		
		logger.info(f"Payslip uploaded successfully: {payslip_id} for user {user_id}")
		
		# Retornar el payslip creado
		return Payslip(
			id=payslip_id,
			user_id=user_id,
			filename=file.filename,
			file_path=file_path,
			file_size=file_size,
			period_month=period_month,
			period_year=period_year,
			company_name=company_name,
			employee_name=employee_name,
			employee_nif=employee_nif,
			gross_salary=gross_salary,
			net_salary=net_salary,
			irpf_withholding=irpf_withholding,
			irpf_percentage=irpf_percentage,
			ss_contribution=ss_contribution,
			extraction_status=extraction_status,
			extracted_data=extracted_data_json,
			analysis_summary=summary
		)
		
	except Exception as e:
		logger.error(f"Error uploading payslip: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail=f"Error procesando nómina: {str(e)}")


@router.get("/", response_model=List[Payslip])
async def list_payslips(
	current_user: dict = Depends(get_current_user)
):
	"""
	Lista todas las nóminas del usuario autenticado.
	
	Args:
		current_user: Usuario autenticado
		
	Returns:
		List[Payslip]: Lista de nóminas del usuario
	"""
	try:
		user_id = current_user.user_id
		
		db = await get_db_client()
		result = await db.execute("""
			SELECT * FROM payslips
			WHERE user_id = ?
			ORDER BY period_year DESC, period_month DESC
		""", [user_id])
		
		rows = result.rows
		
		payslips = []
		for row in rows:
			payslips.append(Payslip(
				id=row[0],
				user_id=row[1],
				filename=row[2],
				file_path=row[3],
				file_size=row[4],
				upload_date=row[5],
				period_month=row[6],
				period_year=row[7],
				company_name=row[8],
				employee_name=row[9],
				employee_nif=row[10],
				gross_salary=row[11],
				net_salary=row[12],
				irpf_withholding=row[13],
				irpf_percentage=row[14],
				ss_contribution=row[15],
				extraction_status=row[16],
				extracted_data=row[17],
				analysis_summary=row[18],
				created_at=row[19],
				updated_at=row[20]
			))
		
		return payslips
		
	except Exception as e:
		logger.error(f"Error listing payslips: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail=f"Error obteniendo nóminas: {str(e)}")


@router.get("/{payslip_id}", response_model=Payslip)
async def get_payslip(
	payslip_id: str,
	current_user: dict = Depends(get_current_user)
):
	"""
	Obtiene una nómina específica por ID.
	
	Args:
		payslip_id: ID de la nómina
		current_user: Usuario autenticado
		
	Returns:
		Payslip: Nómina solicitada
	"""
	try:
		user_id = current_user.user_id
		
		db = await get_db_client()
		result = await db.execute("""
			SELECT * FROM payslips
			WHERE id = ? AND user_id = ?
		""", [payslip_id, user_id])
		
		rows = result.rows
		
		if not rows or len(rows) == 0:
			raise HTTPException(status_code=404, detail="Nómina no encontrada")
		
		row = rows[0]
		
		return Payslip(
			id=row[0],
			user_id=row[1],
			filename=row[2],
			file_path=row[3],
			file_size=row[4],
			upload_date=row[5],
			period_month=row[6],
			period_year=row[7],
			company_name=row[8],
			employee_name=row[9],
			employee_nif=row[10],
			gross_salary=row[11],
			net_salary=row[12],
			irpf_withholding=row[13],
			irpf_percentage=row[14],
			ss_contribution=row[15],
			extraction_status=row[16],
			extracted_data=row[17],
			analysis_summary=row[18],
			created_at=row[19],
			updated_at=row[20]
		)
		
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error getting payslip: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail=f"Error obteniendo nómina: {str(e)}")


@router.post("/{payslip_id}/analyze")
async def analyze_payslip_with_agent(
	payslip_id: str,
	question: str = "Analiza mi nómina y dame recomendaciones",
	current_user: dict = Depends(get_current_user)
):
	"""
	Analiza una nómina usando el agente de IA.
	
	Args:
		payslip_id: ID de la nómina
		question: Pregunta específica sobre la nómina (opcional)
		current_user: Usuario autenticado
		
	Returns:
		Dict con análisis del agente
	"""
	try:
		user_id = current_user.user_id
		
		# Obtener nómina de la BD
		db = await get_db_client()
		result = await db.execute("""
			SELECT * FROM payslips
			WHERE id = ? AND user_id = ?
		""", [payslip_id, user_id])
		
		rows = result.rows
		
		if not rows or len(rows) == 0:
			raise HTTPException(status_code=404, detail="Nómina no encontrada")
		
		row = rows[0]
		
		payslip = Payslip(
			id=row[0],
			user_id=row[1],
			filename=row[2],
			file_path=row[3],
			file_size=row[4],
			upload_date=row[5],
			period_month=row[6],
			period_year=row[7],
			company_name=row[8],
			employee_name=row[9],
			employee_nif=row[10],
			gross_salary=row[11],
			net_salary=row[12],
			irpf_withholding=row[13],
			irpf_percentage=row[14],
			ss_contribution=row[15],
			extraction_status=row[16],
			extracted_data=row[17],
			analysis_summary=row[18],
			created_at=row[19],
			updated_at=row[20]
		)
		
		# Verificar que la extracción fue exitosa
		if payslip.extraction_status != "completed":
			raise HTTPException(
				status_code=400,
				detail="No se pudo extraer información de esta nómina. Verifica que el PDF sea legible."
			)
		
		# Llamar al agente especializado de nóminas
		agent = get_payslip_agent()
		
		response = await agent.analyze(
			payslip_data={
				"period_month": payslip.period_month,
				"period_year": payslip.period_year,
				"company_name": payslip.company_name,
				"employee_name": payslip.employee_name,
				"gross_salary": payslip.gross_salary,
				"net_salary": payslip.net_salary,
				"irpf_withholding": payslip.irpf_withholding,
				"irpf_percentage": payslip.irpf_percentage,
				"ss_contribution": payslip.ss_contribution
			},
			user_question=question
		)
		
		return JSONResponse(content={
			"success": True,
			"payslip_id": payslip_id,
			"period": f"{payslip.period_month}/{payslip.period_year}",
			"question": question,
			"analysis": response.content,
			"metadata": response.metadata
		})
		
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error analyzing payslip with agent: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail=f"Error analizando nómina: {str(e)}")


@router.delete("/{payslip_id}")
async def delete_payslip(
	payslip_id: str,
	current_user: dict = Depends(get_current_user)
):
	"""
	Elimina una nómina.
	
	Args:
		payslip_id: ID de la nómina
		current_user: Usuario autenticado
		
	Returns:
		Dict con confirmación
	"""
	try:
		user_id = current_user.user_id
		
		# Obtener nómina para eliminar archivo
		db = await get_db_client()
		result = await db.execute("""
			SELECT file_path FROM payslips
			WHERE id = ? AND user_id = ?
		""", [payslip_id, user_id])
		
		rows = result.rows
		
		if not rows or len(rows) == 0:
			raise HTTPException(status_code=404, detail="Nómina no encontrada")
		
		file_path = rows[0][0]
		
		# Eliminar archivo físico
		if os.path.exists(file_path):
			os.remove(file_path)
		
		# Eliminar registro de BD
		await db.execute("""
			DELETE FROM payslips
			WHERE id = ? AND user_id = ?
		""", [payslip_id, user_id])
		
		logger.info(f"Payslip deleted: {payslip_id} for user {user_id}")
		
		return JSONResponse(content={
			"success": True,
			"message": "Nómina eliminada correctamente",
			"payslip_id": payslip_id
		})
		
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error deleting payslip: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail=f"Error eliminando nómina: {str(e)}")