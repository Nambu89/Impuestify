	async def analyze_payslip(self, pdf_path: str) -> Dict[str, Any]:
		"""
		Analyze payslip PDF and extract key data.
		
		Returns data compatible with notification analysis response.
		
		Args:
			pdf_path: Path to PDF file
			
		Returns:
			Dict with analysis data compatible with notifications endpoint
		"""
		try:
			logger.info(f"📊 Analyzing payslip PDF: {pdf_path}")
			
			# Extract text from PDF using PyMuPDF
			import pymupdf
			import hashlib
			
			doc = pymupdf.open(pdf_path)
			pdf_text = ""
			for page in doc:
				pdf_text += page.get_text()
			doc.close()
			
			# Calculate file hash
			with open(pdf_path, "rb") as f:
				file_hash = hashlib.sha256(f.read()).hexdigest()
			
			logger.info(f"✅ Extracted {len(pdf_text)} characters from PDF")
			
			# Use gpt-5-mini to extract structured data
			extraction_prompt = f"""Extrae los datos clave de esta nómina española.

TEXTO DE LA NÓMINA:
```
{pdf_text[:4000]}
```

Extrae y devuelve en formato JSON:
{{
	"period_month": "Noviembre",
	"period_year": 2025,
	"company_name": "Nombre de la empresa",
	"employee_name": "Nombre del empleado",
	"gross_salary": 2934.34,
	"net_salary": 2211.63,
	"irpf_withholding": 532.88,
	"irpf_percentage": 18.15,
	"ss_contribution": 189.81,
	"salary_base": 1123.47,
	"complements": 1810.87,
	"region": "Aragón"
}}

Si no encuentras un dato, usa null. Sé preciso con los números.
"""
			
			response = self._client.chat.completions.create(
				model="gpt-5-mini",
				messages=[
					{"role": "system", "content": "Eres un experto extractor de datos de nóminas españolas. Respondes SOLO en JSON válido."},
					{"role": "user", "content": extraction_prompt}
				],
				temperature=1,
				response_format={"type": "json_object"}
			)
			
			import json
			payslip_data = json.loads(response.choices[0].message.content)
			
			logger.info(f"✅ Extracted: {payslip_data.get('period_month')}/{payslip_data.get('period_year')}")
			
			# Generate analysis using agent's analyze method
			analysis_response = await self.analyze(
				payslip_data=payslip_data,
				user_question=None
			)
			
			# Return in format compatible with notifications endpoint
			return {
				"type": "Nómina",
				"summary": analysis_response.content,
				"file_hash": file_hash,
				"notification_date": f"{payslip_data.get('period_year', 2025)}-{payslip_data.get('period_month', 'Enero')}",
				"deadlines": [],
				"region": {
					"region": payslip_data.get('region', 'No especificada'),
					"is_foral": False
				},
				"severity": "low",
				"reference_links": [],
				"payslip_data": payslip_data
			}
			
		except Exception as e:
			logger.error(f"❌ Error analyzing payslip: {e}", exc_info=True)
			return {
				"type": "Nómina",
				"summary": f"Error al analizar la nómina: {str(e)}",
				"file_hash": "unknown",
				"notification_date": datetime.now().strftime("%Y-%m-%d"),
				"deadlines": [],
				"region": {"region": "No especificada", "is_foral": False},
				"severity": "low",
				"reference_links": [],
				"payslip_data": {}
			}
