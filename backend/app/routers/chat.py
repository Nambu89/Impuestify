"""
Chat Router for Impuestify

Handles question-answering using:
- Keyword search in Turso Database (embeddings pre-computed)
- OpenAI for answer generation
- TaxAgent for orchestration
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time
import logging

from app.database.turso_client import TursoClient
from app.agents.tax_agent import TaxAgent
from app.config import settings
from app.utils.irpf_calculator import IRPFCalculator
from app.utils.region_detector import RegionDetector
from app.services.conversation_service import ConversationService
from app.services.conversation_cache import ConversationCache
from app.auth.jwt_handler import get_current_user, TokenData
from app.auth.subscription_guard import require_active_subscription
from app.security import sql_validator, guardrails_system, rate_limit_ask
from app.security.content_restriction import detect_autonomo_query, get_autonomo_block_response
from app.services.subscription_service import SubscriptionAccess
from app.metrics import record_tokens, record_request, record_error, record_rag_search, record_llm_latency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


# === Models ===

class QuestionRequest(BaseModel):
	"""Request model for asking a question"""
	question: str = Field(..., min_length=3, max_length=1000, description="Tax question")
	conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
	workspace_id: Optional[str] = Field(None, description="Active workspace ID for context")
	k: Optional[int] = Field(default=5, ge=1, le=10, description="Number of documents to retrieve")


class Source(BaseModel):
	"""Source document model"""
	id: str
	source: str
	page: int
	title: str
	text_preview: str
	score: Optional[float] = None


class ImpuestifyResponse(BaseModel):
	"""Response model from Impuestify"""
	answer: str
	sources: List[Source]
	processing_time: float
	metadata: Dict[str, Any]
	conversation_id: Optional[str] = None


# === Dependencies ===

async def get_db(request: Request) -> TursoClient:
	"""Get database client from app state"""
	if hasattr(request.app.state, 'db_client') and request.app.state.db_client:
		return request.app.state.db_client
	raise HTTPException(
		status_code=503,
		detail="Database not connected. Check Turso configuration."
	)


# === Helper Functions ===

async def fts_search(db: TursoClient, query: str, k: int = 5) -> List[Dict]:
	"""
	Full-text search using SQLite FTS5.
	
	Uses BM25 ranking algorithm for relevance scoring.
	Falls back to LIKE search if FTS5 table doesn't exist.
	
	Enhanced with regional detection: 
	- Detects user's CCAA from query (e.g., "Zaragoza" → "Aragón")
	- Augments search with CCAA name for better regional tax table retrieval
	"""
	try:
		# Clean query for FTS5 (remove special characters)
		clean_query = ''.join(c for c in query if c.isalnum() or c.isspace())
		keywords = clean_query.split()
		
		if not keywords:
			logger.warning("Query is empty after cleaning")
			return []
		
		# === Detect user's region from query ===
		from app.utils.region_detector import RegionDetector
		detector = RegionDetector()
		region_info = detector.detect_from_text(query)
		
		detected_ccaa = None
		if region_info['confidence'] in ['high', 'medium']:
			detected_ccaa = region_info['region']
			logger.info(f"📍 Detected CCAA: {detected_ccaa} (confidence: {region_info['confidence']})")
			
			# Augment query with CCAA name
			ccaa_keywords = detected_ccaa.split()
			keywords.extend(ccaa_keywords)
			logger.info(f"🔍 Enhanced keywords: {keywords}")
		
		# Strategy 1: OR query (any keyword matches) - High Recall
		fts_query = ' OR '.join([f'"{kw}"' for kw in keywords])
		
		logger.info(f"🔍 FTS5 Search Query: {fts_query}")
		
		# Detect if user mentions a Hacienda Foral region
		query_lower = query.lower()
		foral_keywords = {
			'navarra': 'navarra',
			'euskadi': 'euskadi',
			'país vasco': 'euskadi',
			'pais vasco': 'euskadi',
			'guipúzcoa': 'guipuzkoa',
			'gipuzkoa': 'guipuzkoa',
			'guipuzkoa': 'guipuzkoa',
			'vizcaya': 'bizkaia',
			'bizkaia': 'bizkaia',
			'álava': 'araba',
			'alava': 'araba',
			'araba': 'araba'
		}
		
		detected_foral = None
		for keyword, region in foral_keywords.items():
			if keyword in query_lower:
				detected_foral = region
				break
		
		# Build SQL with metadata filter (parameterized)
		metadata_filter = ""
		metadata_params = []
		if detected_foral:
			logger.info(f"📍 Detected Hacienda Foral: {detected_foral}, filtering for regional docs")
			metadata_filter = "AND (LOWER(d.filename) LIKE ? OR LOWER(d.source) LIKE ?)"
			foral_pattern = f"%{detected_foral}%"
			metadata_params = [foral_pattern, foral_pattern]
		else:
			# Prioritize AEAT documents: exclude Haciendas Forales
			logger.info("📍 No foral region detected, prioritizing AEAT general documents")
			foral_exclusions = ['navarra', 'guipuzkoa', 'gipuzkoa', 'bizkaia', 'araba', 'álava', 'alava']
			exclusion_parts = " AND ".join(["LOWER(d.filename) NOT LIKE ?" for _ in foral_exclusions])
			metadata_filter = f"AND ({exclusion_parts})"
			metadata_params = [f"%{region}%" for region in foral_exclusions]
		
		# === CCAA-Specific Tax Table Search (Phase 1) ===
		ccaa_tax_table_chunks = []
		if detected_ccaa and "Comunidad" not in detected_ccaa and detected_ccaa != "General (territorio común)":
			logger.info(f"🎯 Phase 1: Searching for {detected_ccaa} tax table...")
			
			ccaa_search_terms = detected_ccaa.split() + ["escala", "Base", "liquidable"]
			ccaa_fts_query = ' OR '.join([f'"{term}"' for term in ccaa_search_terms])
			
			# Check if it's a foral region - use their specific manuals
			foral_doc_mapping = {
				'País Vasco': ['Bizkaia', 'Guipuzkoa', 'Araba'],
				'Bizkaia': ['Bizkaia'],
				'Vizcaya': ['Bizkaia'],
				'Gipuzkoa': ['Guipuzkoa'],
				'Guipúzcoa': ['Guipuzkoa'],
				'Araba': ['Araba'],
				'Álava': ['Araba'],
				'Navarra': ['Navarra'],
			}
			
			# Determine which document filter to use
			foral_match = None
			for key, docs in foral_doc_mapping.items():
				if key.lower() in detected_ccaa.lower():
					foral_match = docs
					break
			
			if foral_match:
				# Search in foral manual(s) — parameterized
				doc_conditions = ' OR '.join(["d.filename LIKE ?" for _ in foral_match])
				doc_params = [f"%{doc}%" for doc in foral_match]
				ccaa_sql = f"""
				SELECT 
					c.id,
					c.content,
					c.page_number,
					d.filename,
					d.title,
					fts.rank
				FROM document_chunks_fts fts
				JOIN document_chunks c ON c.id = fts.chunk_id
				JOIN documents d ON d.id = c.document_id
				WHERE document_chunks_fts MATCH ? 
				AND ({doc_conditions})
				ORDER BY rank 
				LIMIT 5
				"""
				logger.info(f"🎯 Searching in foral docs: {foral_match}")
			else:
				# Search in AEAT manual for non-foral CCAA
				ccaa_sql = f"""
				SELECT 
					c.id,
					c.content,
					c.page_number,
					d.filename,
					d.title,
					fts.rank
				FROM document_chunks_fts fts
				JOIN document_chunks c ON c.id = fts.chunk_id
				JOIN documents d ON d.id = c.document_id
				WHERE document_chunks_fts MATCH ? 
				AND d.filename LIKE '%Renta_2024._Parte_1%'
				AND c.page_number BETWEEN 1230 AND 1245
				{metadata_filter}
				ORDER BY rank 
				LIMIT 3
				"""
			
			try:
				ccaa_params = [ccaa_fts_query] + (doc_params if foral_match else metadata_params)
				ccaa_result = await db.execute(ccaa_sql, ccaa_params)
				
				if ccaa_result.rows:
					logger.info(f"✅ Found {len(ccaa_result.rows)} CCAA tax table chunks")
					for row in ccaa_result.rows:
						ccaa_tax_table_chunks.append({
							"id": row['id'],
							"text": row['content'],
							"page": row['page_number'],
							"source": row['filename'],
							"title": f"Tabla IRPF - {detected_ccaa}",
							"similarity": abs(float(row.get('rank', -1.0))) + 100  # Boost score
						})
				else:
					# Check if it's a foral region (expected to not have tables in AEAT docs)
					foral_regions = ['País Vasco', 'Navarra', 'Euskadi']
					if any(foral in detected_ccaa for foral in foral_regions):
						logger.info(f"ℹ️ {detected_ccaa} uses foral tax system (not in AEAT docs)")
					else:
						logger.warning(f"⚠️ No CCAA tax table found for {detected_ccaa}")
			except Exception as e:
				logger.error(f"Error in CCAA tax table search: {e}")
		
		# === Phase 2: General FTS5 Search ===
		try:
			sql = f"""
			SELECT 
				c.id,
				c.content,
				c.page_number,
				d.filename,
				d.title,
				fts.rank
			FROM document_chunks_fts fts
			JOIN document_chunks c ON c.id = fts.chunk_id
			JOIN documents d ON d.id = c.document_id
			WHERE document_chunks_fts MATCH ? 
			{metadata_filter}
			ORDER BY rank 
			LIMIT ?
			"""
			
			result = await db.execute(sql, [fts_query] + metadata_params + [k])
			
			if result.rows:
				logger.info(f"✅ FTS5 found {len(result.rows)} results")
				chunks = []
				for row in result.rows:
					chunks.append({
						"id": row['id'],
						"text": row['content'],
						"page": row['page_number'],
						"source": row['filename'],
						"title": row['title'] or row['filename'],
						"similarity": abs(float(row.get('rank', -1.0)))
					})
				
				# Combine CCAA-specific chunks (if any) with general results
				return ccaa_tax_table_chunks + chunks
			else:
				logger.warning("⚠️ FTS5 found 0 results")
				return ccaa_tax_table_chunks  # Return CCAA chunks if available
				
		except Exception as fts_error:
			# FTS5 table doesn't exist or query error, fall back to LIKE search
			logger.warning(f"FTS5 error, falling back to LIKE search: {fts_error}")
			
			keywords = query.lower().split()[:5]
			where_conditions = " OR ".join([
				f"LOWER(c.content) LIKE ?"
				for _ in keywords
			])
			
			sql = f"""
			SELECT 
				c.id,
				c.content,
				c.page_number,
				d.filename,
				d.title,
				1.0 as relevance_score
			FROM document_chunks c
			JOIN documents d ON d.id = c.document_id
			WHERE {where_conditions}
			LIMIT ?
			"""
			
			params = [f"%{kw}%" for kw in keywords] + [k]
			result = await db.execute(sql, params)
			
			chunks = []
			for row in result.rows:
				chunks.append({
					"id": row['id'],
					"text": row['content'],
					"page": row['page_number'],
					"source": row['filename'],
					"title": row['title'] or row['filename'],
					"similarity": 0.5
				})
			
			return ccaa_tax_table_chunks + chunks
		
	except Exception as e:
		logger.error(f"Error in FTS search: {e}", exc_info=True)
		return []


# === Routes ===

@router.post("/ask", response_model=ImpuestifyResponse)
async def ask_question(
	req: Request,
	request: QuestionRequest,
	db: TursoClient = Depends(get_db),
	current_user: TokenData = Depends(get_current_user),
	access: SubscriptionAccess = Depends(require_active_subscription)
):
	"""
	Ask a tax question to Impuestify with optional conversation context.
	
	- **question**: Your tax question in Spanish
	- **conversation_id**: Optional conversation ID for context (creates new if not provided)
	- **k**: Number of relevant documents to retrieve (default: 5)
	"""
	start_time = time.time()
	
	try:
		# === SECURITY LAYER 1: SQL Injection Detection ===
		sql_check = sql_validator.validate_user_input(request.question)
		if not sql_check.is_safe:
			logger.warning(f"🚨 SQL injection blocked: {sql_check.violations}")
			raise HTTPException(
				status_code=400,
				detail={
					"error": "Security violation detected",
					"type": "sql_injection",
					"risk_level": sql_check.risk_level
				}
			)
		
		# === SECURITY LAYER 2: Guardrails Validation ===
		guardrails_check = guardrails_system.validate_input(request.question)
		if not guardrails_check.is_safe:
			logger.warning(f"⚠️ Guardrails violation: {guardrails_check.violations}")
			if guardrails_check.risk_level == "critical":
				raise HTTPException(
					status_code=400,
					detail={
						"error": "Question violates safety guidelines",
						"suggestions": guardrails_check.suggestions,
						"risk_level": guardrails_check.risk_level
					}
				)
			logger.info(f"Non-critical guardrail: {guardrails_check.risk_level}")
		
		# === CONTENT RESTRICTION: Autonomo detection ===
		if not access.is_owner and detect_autonomo_query(request.question):
			return ImpuestifyResponse(
				answer=get_autonomo_block_response(),
				sources=[],
				processing_time=time.time() - start_time,
				conversation_id=request.conversation_id,
				metadata={"type": "content_restriction", "restricted_topic": "autonomo"}
			)

		logger.info(f"Nueva consulta: {request.question[:100]}... (conversation_id: {request.conversation_id})")
		
		# Initialize conversation service
		conv_service = ConversationService(db)
		
		# 1. Get or create conversation
		conversation_id = request.conversation_id
		if not conversation_id:
			# Create new conversation
			conversation = await conv_service.create_conversation(
				user_id=current_user.user_id,
				title=request.question[:50] + "..." if len(request.question) > 50 else request.question
			)
			conversation_id = conversation["id"]
			logger.info(f"✅ Created new conversation: {conversation_id}")
		else:
			# Verify conversation exists and belongs to user
			conversation = await conv_service.get_conversation(conversation_id, current_user.user_id)
			if not conversation:
				raise HTTPException(status_code=404, detail="Conversation not found")
		
		# === GREETING DETECTION ===
		# If user sends a simple greeting, respond cordially without RAG search
		if guardrails_system.is_greeting(request.question.strip()):
			logger.info("👋 Greeting detected, sending friendly welcome")
			greeting_response = (
				"¡Hola! 👋 Soy Impuestify, tu asistente fiscal inteligente.\n\n"
				"Estoy aquí para ayudarte con preguntas sobre:\n"
				"- 💰 IRPF y declaración de la renta (Modelo 100)\n"
				"- 📋 Análisis de nóminas y retenciones\n"
				"- 📉 Deducciones y exenciones fiscales\n"
				"- 📬 Notificaciones de la AEAT\n\n"
				"¿En qué puedo ayudarte hoy?"
			)
			
			# Save messages to conversation
			await conv_service.add_message(conversation_id, "user", request.question)
			await conv_service.add_message(conversation_id, "assistant", greeting_response)
			
			return ImpuestifyResponse(
				answer=greeting_response,
				sources=[],
				processing_time=time.time() - start_time,
				conversation_id=conversation_id,
				metadata={"type": "greeting", "search_method": "none"}
			)
		
		# 2. Initialize cache service
		upstash_client = getattr(req.app.state, 'upstash_client', None)
		cache = ConversationCache(upstash_client)
		
		# 3. Load conversation context (cache-first strategy)
		conversation_history = []
		notification_context = ""
		notification_metadata = {}
		cached_context = None
		
		# Try cache first
		cached_context = await cache.get_context(conversation_id)
		
		if cached_context:
			# Cache HIT
			conversation_history = cached_context.get("recent_messages", [])
			notification_context = cached_context.get("notification_content", "")
			notification_metadata = cached_context.get("notification_metadata", {})
			
			await cache.refresh_ttl(conversation_id)
			
			logger.info(f"💾 Using cached context for conversation {conversation_id}")
		else:
			# Cache MISS - load from database
			conversation_history = await conv_service.get_recent_messages(conversation_id, limit=20)
			logger.info(f"📂 Loaded {len(conversation_history)} messages from database")
			
		# === Load workspace context if workspace_id provided ===
		workspace_context = ""
		workspace_files_info = []
		if request.workspace_id:
			logger.info(f"📁 Loading workspace context for: {request.workspace_id}")
			try:
				# Verify workspace ownership
				ws_result = await db.execute(
					"SELECT id, name FROM workspaces WHERE id = ? AND user_id = ?",
					[request.workspace_id, current_user.user_id]
				)
				if ws_result.rows:
					# Load workspace files with extracted text
					files_result = await db.execute(
						"""
						SELECT filename, file_type, extracted_text
						FROM workspace_files
						WHERE workspace_id = ? AND processing_status = 'completed'
						""",
						[request.workspace_id]
					)

					if files_result.rows:
						docs_context = []
						for f in files_result.rows:
							if f.get("extracted_text"):
								doc_info = f"--- {f['filename']} ({f['file_type']}) ---\n{f['extracted_text'][:5000]}"
								docs_context.append(doc_info)
								workspace_files_info.append({
									"filename": f["filename"],
									"file_type": f["file_type"]
								})

						if docs_context:
							workspace_context = "\n\n".join(docs_context)
							logger.info(f"📁 Loaded {len(docs_context)} documents from workspace")
			except Exception as e:
				logger.error(f"Error loading workspace context: {e}")

		# Check if there's a notification in the conversation history
		for msg in conversation_history:
			if msg.get("role") == "assistant" and msg.get("metadata"):
				metadata = msg.get("metadata", {})
				if "notification_id" in metadata:
					notification_context = f"""CONTEXTO DE NOTIFICACIÓN DEL USUARIO:
{msg.get('content', '')}

INFORMACIÓN ADICIONAL DE LA NOTIFICACIÓN:
- Tipo: {metadata.get('notification_type', 'N/A')}
- Región: {metadata.get('region', 'N/A')}
- Plazos: {metadata.get('deadlines', 'N/A')}

---
"""
					notification_metadata = {
						"notification_id": metadata.get("notification_id"),
						"notification_type": metadata.get("notification_type"),
						"region": metadata.get("region"),
						"deadlines": metadata.get("deadlines")
					}
					logger.info(f"📋 Found notification context in conversation history")
					break
		
		# 4. Search relevant chunks using Hybrid Retriever (FTS5 + Vector + RRF)
		search_start = time.time()
		from app.utils.hybrid_retriever import HybridRetriever, get_query_embedding
		retriever = HybridRetriever(db_client=db)
		query_embedding = await get_query_embedding(request.question)
		relevant_chunks = await retriever.search(
			query=request.question,
			query_embedding=query_embedding,
			k=request.k or 5,
		)
		search_time = time.time() - search_start
		
		if not relevant_chunks:
			# Save user message even if no context found
			await conv_service.add_message(conversation_id, "user", request.question)
			
			no_context_answer = "Lo siento, no encontré información relevante en la base de datos para responder tu pregunta. Por favor, intenta reformular tu consulta o usar palabras clave más específicas."
			
			# Save assistant response
			await conv_service.add_message(conversation_id, "assistant", no_context_answer)
			
			# Update cache even with no context
			updated_history = await conv_service.get_recent_messages(conversation_id, limit=20)
			await cache.set_context(conversation_id, {
				"notification_content": notification_context,
				"notification_metadata": notification_metadata,
				"recent_messages": updated_history
			})
			
			return TaxIAResponse(
				answer=no_context_answer,
				sources=[],
				processing_time=time.time() - start_time,
				conversation_id=conversation_id,
				metadata={
					"search_time": search_time,
					"chunks_found": 0,
					"search_method": "fts5"
				}
			)
		
		# 5. Generate answer using appropriate agent
		agent_start = time.time()

		# Prepare RAG context from retrieved chunks
		rag_context = "\n\n".join([
			f"Fuente: {chunk['title']} (Página {chunk['page']})\n{chunk['text']}"
			for chunk in relevant_chunks
		])

		# Combine notification context (priority) with RAG context
		combined_context = notification_context + rag_context if notification_context else rag_context

		# Prepare sources for metadata
		sources_data = [
			{
				"id": chunk['id'],
				"source": chunk['source'],
				"page": chunk['page'],
				"title": chunk['title'],
				"score": chunk['similarity']
			}
			for chunk in relevant_chunks
		]

		# Prepare conversation history for agent
		formatted_history = []
		for msg in conversation_history[-10:]:  # Last 10 messages (5 exchanges)
			formatted_history.append({
				"role": msg.get("role"),
				"content": msg.get("content")
			})

		# === Choose agent based on context ===
		restricted_mode = not access.is_owner

		if workspace_context:
			# Use WorkspaceAgent for workspace queries
			from app.agents.workspace_agent import get_workspace_agent
			agent = get_workspace_agent()
			logger.info(f"📁 Calling WorkspaceAgent with {len(workspace_files_info)} documents")
			agent_response = await agent.run(
				query=request.question,
				context=workspace_context,
				sources=sources_data,
				conversation_history=formatted_history,
				user_id=current_user.user_id,
				workspace_id=request.workspace_id,
				restricted_mode=restricted_mode
			)
		else:
			# Use TaxAgent for general tax queries
			tax_agent = TaxAgent()
			logger.info(f"🤖 Calling TaxAgent with {len(formatted_history)} history messages")
			agent_response = await tax_agent.run(
				query=request.question,
				context=combined_context,
				sources=sources_data,
				conversation_history=formatted_history,
				use_tools=True,
				restricted_mode=restricted_mode
			)
		
		answer = agent_response.content
		
		logger.info(f"🤖 TaxAgent response length: {len(answer)}")
		agent_time = time.time() - agent_start
		
		# === SECURITY LAYER 3: Output Validation ===
		output_check = guardrails_system.validate_output(
			llm_response=answer,
			user_question=request.question,
			sources=sources_data
		)
		
		if not output_check.is_safe:
			logger.warning(f"⚠️ Output guardrail violation: {output_check.violations}")
			answer = guardrails_system.apply_safety_wrapper(
				answer,
				risk_level=output_check.risk_level
			)
		
		# 6. Save user message
		await conv_service.add_message(
			conversation_id=conversation_id,
			role="user",
			content=request.question
		)
		
		# 7. Save assistant message with sources
		assistant_msg = await conv_service.add_message(
			conversation_id=conversation_id,
			role="assistant",
			content=answer,
			metadata={"sources": sources_data}
		)
		
		# Link sources to assistant message
		await conv_service.add_message_sources(assistant_msg["id"], sources_data)
		
		# 8. Update cache with new messages
		updated_history = await conv_service.get_recent_messages(conversation_id, limit=20)
		
		await cache.set_context(conversation_id, {
			"notification_content": notification_context,
			"notification_metadata": notification_metadata,
			"recent_messages": updated_history
		})
		logger.info(f"💾 Cache updated for conversation {conversation_id}")
		
		# 9. Format sources for response
		sources = [
			Source(
				id=chunk['id'],
				source=chunk['source'],
				page=chunk['page'],
				title=chunk['title'],
				text_preview=chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text'],
				score=round(chunk['similarity'], 4)
			)
			for chunk in relevant_chunks
		]
		
		processing_time = time.time() - start_time
		
		# Record metrics
		record_rag_search(len(relevant_chunks), search_time)
		record_llm_latency(settings.OPENAI_MODEL, agent_time)
		record_request("ask", "POST", 200, "authenticated")
		
		logger.info(f"✅ Consulta procesada: {processing_time:.2f}s, {len(sources)} fuentes, conversation: {conversation_id}")
		
		# 10. Return response
		return ImpuestifyResponse(
			answer=answer,
			sources=sources,
			processing_time=processing_time,
			conversation_id=conversation_id,
			metadata={
				"search_time": search_time,
				"agent_time": agent_time,
				"chunks_found": len(relevant_chunks),
				"search_method": "fts5",
				"cached": bool(cached_context),
				"notification_analyzed": bool(notification_context),
				"model": settings.OPENAI_MODEL,
				"conversation_messages": len(conversation_history),
				"security": {
					"sql_validation": sql_check.risk_level,
					"input_guardrails": guardrails_check.risk_level,
					"output_guardrails": output_check.risk_level,
					"violations": (
						guardrails_check.violations + output_check.violations 
						if not guardrails_check.is_safe or not output_check.is_safe 
						else []
					)
				}
			}
		)
		
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error processing question: {e}", exc_info=True)
		raise HTTPException(
			status_code=500,
			detail=f"Error processing question: {str(e)}"
		)