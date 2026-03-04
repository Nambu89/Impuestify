"""
User Memory Service for TaxIA

Implements long-term memory for users using:
1. Upstash Vector for semantic memory (facts about user)
2. Turso DB for structured profile data

This allows the system to remember user information across sessions:
- CCAA of residence
- Employment situation
- Family situation
- Previous questions and preferences
"""
import os
import logging
import json
import hashlib
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import upstash-vector
try:
    from upstash_vector import Index
    UPSTASH_VECTOR_AVAILABLE = True
except ImportError:
    UPSTASH_VECTOR_AVAILABLE = False
    logger.warning("upstash-vector not installed. User memory will use DB only.")


@dataclass
class UserFact:
    """A fact about the user stored in memory."""
    fact_id: str
    fact_type: str  # 'residence', 'employment', 'family', 'preference', 'context'
    content: str
    confidence: float = 1.0
    source: str = "user_statement"  # 'user_statement', 'inferred', 'workspace'
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class UserProfile:
    """Structured user profile stored in Turso DB."""
    user_id: str
    ccaa_residencia: Optional[str] = None
    situacion_laboral: Optional[str] = None  # 'asalariado', 'autonomo', 'pensionista', 'desempleado'
    tiene_vivienda: Optional[bool] = None
    primera_vivienda: Optional[bool] = None
    fecha_nacimiento: Optional[str] = None
    # NEW: Extended fiscal profile fields
    edad: Optional[int] = None  # User's age
    ingresos_brutos: Optional[float] = None  # Annual gross income
    donation_pending: Optional[float] = None  # Pending donation amount
    donation_type: Optional[str] = None  # 'money', 'property', 'inheritance'
    donation_from: Optional[str] = None  # 'mother', 'father', 'other'
    datos_fiscales: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class UserMemoryService:
    """
    Service for managing long-term user memory.
    
    Uses two storage layers:
    1. **Upstash Vector**: Semantic memory (facts, preferences, context)
    2. **Turso DB**: Structured profile (CCAA, employment, etc.)
    
    Features:
    - Extract facts from user messages
    - Store and retrieve semantic memories
    - Maintain structured profile
    - Cross-session memory persistence
    """
    
    # Types of facts we can extract and store
    FACT_TYPES = {
        'residence': ['vivo en', 'resido en', 'soy de', 'vivo a', 'residencia en', 'domicilio en'],
        'employment': ['trabajo como', 'soy autónomo', 'soy asalariado', 'trabajo en', 'mi trabajo', 'cobro', 'gano'],
        'family': ['mi madre', 'mi padre', 'mi hijo', 'mi hija', 'mi pareja', 'mi cónyuge', 'estoy casado', 'tengo hijos'],
        'property': ['comprar casa', 'comprar piso', 'primera vivienda', 'mi casa', 'mi piso', 'hipoteca'],
        'donation': ['me va a donar', 'donación', 'me han donado', 'voy a donar'],
        'tax_context': ['declaración', 'irpf', 'iva', 'modelo', 'hacienda', 'tributos'],
    }
    
    # Regex patterns for numeric value extraction
    NUMERIC_PATTERNS = {
        # Age patterns: "tengo 37 años", "cumplo 37", "37 años"
        'age': [
            r'(?:tengo|cumplo|cumplire|cumplire)\s*(\d+)\s*(?:anos|añitos)',
            r'(\d+)\s*(?:anos|añitos?)\s*(?:cumplidos|cumplire)',
            r'edad\s*(?:de\s*)?(\d+)\s*(?:anos)?',
        ],
        # Income patterns: "gano 37500", "37500€ al año", "37500 brutos"
        'income': [
            r'(?:gano|percibo|facturo|tengo\s*unos?)\s*(?:de\s*)?(\d+(?:[,.]\d+)?)\s*(?:€|euritos?)?\s*(?:brutos?|anuales?|al año)?',
            r'ingresos\s*(?:de|anuales?|brutos?)?\s*(?:de\s*)?(\d+(?:[,.]\d+)?)',
            r'sueldo\s*(?:de|neto|bruto)?\s*(?:de\s*)?(\d+(?:[,.]\d+)?)',
            r'(\d+(?:[,.]\d+)?)\s*(?:€|euros?)?\s*(?:brutos?|anuales?|al año)',
        ],
        # Donation amount patterns: "40000€", "40.000 euros"
        'donation_amount': [
            r'(?:donación|de|prestamo|me va a donate)\s*(?:de)?\s*(\d+(?:[,.]\d+)?)\s*(?:€|euros?|euritos?)',
            r'(\d+(?:[,.]\d+)?)\s*(?:€|euros?|euritos?)\s*(?:de donate|donación)',
            r'(?:cantidad|cuánto|cuanto)\s*(?:es|de)\s*(\d+(?:[,.]\d+)?)\s*(?:€|euros?)',
            r'(\d{1,3}(?:[,.]\d{3})*)\s*(?:€|euros?)',  # Matches 40.000 or 40,000
        ],
    }
    
    # CCAA mapping for extraction
    CCAA_MAPPING = {
        'zaragoza': 'Aragón',
        'madrid': 'Comunidad de Madrid',
        'barcelona': 'Cataluña',
        'valencia': 'Comunitat Valenciana',
        'sevilla': 'Andalucía',
        'bilbao': 'País Vasco',
        'vitoria': 'País Vasco',
        'san sebastián': 'País Vasco',
        'pamplona': 'Navarra',
        'toledo': 'Castilla-La Mancha',
        'valladolid': 'Castilla y León',
        'santiago': 'Galicia',
        'a coruña': 'Galicia',
        'málaga': 'Andalucía',
        'alicante': 'Comunitat Valenciana',
        'murcia': 'Murcia',
        'palma': 'Illes Balears',
        'las palmas': 'Canarias',
        'santa cruz': 'Canarias',
        'badajoz': 'Extremadura',
        'cáceres': 'Extremadura',
        'oviedo': 'Asturias',
        'santander': 'Cantabria',
        'logroño': 'La Rioja',
        'ceuta': 'Ceuta',
        'melilla': 'Melilla',
    }
    
    NAMESPACE = "user_memory"
    
    def __init__(
        self,
        db_client=None,
        vector_url: Optional[str] = None,
        vector_token: Optional[str] = None
    ):
        """
        Initialize User Memory Service.
        
        Args:
            db_client: TursoClient instance for DB operations
            vector_url: Upstash Vector REST URL
            vector_token: Upstash Vector REST token
        """
        self.db = db_client
        self.vector_url = vector_url or settings.UPSTASH_VECTOR_REST_URL
        self.vector_token = vector_token or settings.UPSTASH_VECTOR_REST_TOKEN
        self._vector_index = None
        self._openai_client = None
        
        # Initialize vector index if available
        if UPSTASH_VECTOR_AVAILABLE and self.vector_url and self.vector_token:
            try:
                self._vector_index = Index(url=self.vector_url, token=self.vector_token)
                # Initialize OpenAI client for embedding generation
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("🧠 User Memory Service initialized with Upstash Vector + OpenAI embeddings")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Upstash Vector for user memory: {e}")
        else:
            logger.info("📝 User Memory Service initialized (DB only mode)")
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using OpenAI text-embedding-3-large (1536 dims)."""
        if not self._openai_client:
            return None
        try:
            response = self._openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=text,
                dimensions=1536,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"⚠️ Failed to generate embedding: {e}")
            return None
    
    # ========================================
    # NUMERIC VALUE EXTRACTION
    # ========================================
    
    def _extract_numeric_value(self, message: str, pattern_type: str) -> Optional[float]:
        """
        Extract numeric values from message using regex patterns.
        
        Args:
            message: User's message text
            pattern_type: Type of pattern ('age', 'income', 'donation_amount')
            
        Returns:
            Extracted numeric value or None
        """
        patterns = self.NUMERIC_PATTERNS.get(pattern_type, [])
        
        for pattern in patterns:
            try:
                match = re.search(pattern, message.lower())
                if match:
                    # Clean the number (handle both . and , as separators)
                    num_str = match.group(1).replace('.', '').replace(',', '.')
                    value = float(num_str)
                    # Validate reasonable ranges
                    if pattern_type == 'age' and 16 <= value <= 100:
                        return value
                    elif pattern_type == 'income' and 0 < value < 10000000:
                        return value
                    elif pattern_type == 'donation_amount' and 0 < value < 100000000:
                        return value
            except (ValueError, AttributeError) as e:
                logger.debug(f"Pattern match error for {pattern_type}: {e}")
                continue
        
        return None
    
    def _extract_donation_type(self, message: str) -> Optional[str]:
        """Extract donation type from message."""
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ['dinero', 'metálico', 'metalico', 'efectivo', 'transferencia', '€', 'euros']):
            return 'money'
        elif any(kw in message_lower for kw in ['vivienda', 'piso', 'casa', 'inmueble', 'propiedad']):
            return 'property'
        elif any(kw in message_lower for kw in ['herencia', 'fallecido', 'fallece', 'ha muerto']):
            return 'inheritance'
        
        return None
    
    def _extract_donor_relation(self, message: str) -> Optional[str]:
        """Extract donor relation from message."""
        message_lower = message.lower()
        
        if 'mi madre' in message_lower or 'madre' in message_lower:
            return 'mother'
        elif 'mi padre' in message_lower or 'padre' in message_lower:
            return 'father'
        elif 'mi abuela' in message_lower or 'abuela' in message_lower:
            return 'grandmother'
        elif 'mi abuelo' in message_lower or 'abuelo' in message_lower:
            return 'grandfather'
        elif 'mi pareja' in message_lower or 'pareja' in message_lower or 'cónyuge' in message_lower:
            return 'partner'
        
        return None
    
    # ========================================
    # FACT EXTRACTION
    # ========================================
    
    def extract_facts_from_message(self, message: str) -> List[UserFact]:
        """
        Extract facts from a user message.
        
        Args:
            message: User's message text
            
        Returns:
            List of extracted UserFact objects
        """
        facts = []
        message_lower = message.lower()
        
        # Extract residence
        for city, ccaa in self.CCAA_MAPPING.items():
            if city in message_lower:
                facts.append(UserFact(
                    fact_id=self._generate_fact_id('residence', ccaa),
                    fact_type='residence',
                    content=f"El usuario reside en {ccaa} (detectado por mención de {city})",
                    confidence=0.9,
                    source='user_statement'
                ))
                break
        
        # Extract employment situation
        if any(kw in message_lower for kw in ['autónomo', 'autonomo', 'facturo', 'mi negocio']):
            facts.append(UserFact(
                fact_id=self._generate_fact_id('employment', 'autonomo'),
                fact_type='employment',
                content="El usuario es trabajador autónomo",
                confidence=0.85,
                source='user_statement'
            ))
        elif any(kw in message_lower for kw in ['asalariado', 'mi empresa', 'mi jefe', 'nómina', 'nomina']):
            facts.append(UserFact(
                fact_id=self._generate_fact_id('employment', 'asalariado'),
                fact_type='employment',
                content="El usuario es trabajador asalariado",
                confidence=0.85,
                source='user_statement'
            ))
        elif any(kw in message_lower for kw in ['jubilado', 'pensión', 'pensionista']):
            facts.append(UserFact(
                fact_id=self._generate_fact_id('employment', 'pensionista'),
                fact_type='employment',
                content="El usuario es pensionista",
                confidence=0.85,
                source='user_statement'
            ))
        
        # Extract family context
        if 'mi madre' in message_lower or 'mi padre' in message_lower:
            facts.append(UserFact(
                fact_id=self._generate_fact_id('family', 'parents'),
                fact_type='family',
                content="El usuario menciona a sus padres (posible donación/herencia)",
                confidence=0.8,
                source='user_statement'
            ))
        
        # Extract property context
        if any(kw in message_lower for kw in ['primera vivienda', 'comprar casa', 'comprar piso']):
            facts.append(UserFact(
                fact_id=self._generate_fact_id('property', 'first_home'),
                fact_type='property',
                content="El usuario está comprando o planea comprar su primera vivienda",
                confidence=0.9,
                source='user_statement'
            ))
        
        # Extract donation context
        if any(kw in message_lower for kw in ['donar', 'donación', 'donacion']):
            facts.append(UserFact(
                fact_id=self._generate_fact_id('donation', 'pending'),
                fact_type='donation',
                content="El usuario está involucrado en una operación de donación",
                confidence=0.9,
                source='user_statement'
            ))
        
        # ==========================================
        # NEW: Extract numeric values (age, income, donation amounts)
        # ==========================================
        
        # Extract age
        age = self._extract_numeric_value(message, 'age')
        if age:
            facts.append(UserFact(
                fact_id=self._generate_fact_id('age', str(int(age))),
                fact_type='age',
                content=f"El usuario tiene {int(age)} años",
                confidence=0.95,
                source='user_statement'
            ))
        
        # Extract income
        income = self._extract_numeric_value(message, 'income')
        if income:
            facts.append(UserFact(
                fact_id=self._generate_fact_id('income', str(int(income))),
                fact_type='income',
                content=f"El usuario tiene ingresos brutos anuales de {int(income)}€",
                confidence=0.9,
                source='user_statement'
            ))
        
        # Extract donation amount
        donation_amount = self._extract_numeric_value(message, 'donation_amount')
        if donation_amount:
            facts.append(UserFact(
                fact_id=self._generate_fact_id('donation_amount', str(int(donation_amount))),
                fact_type='donation_amount',
                content=f"La operación de donación/trámite es por {int(donation_amount)}€",
                confidence=0.95,
                source='user_statement'
            ))
        
        # Extract donation type
        donation_type = self._extract_donation_type(message)
        if donation_type:
            type_label = 'dinero' if donation_type == 'money' else 'vivienda/inmueble' if donation_type == 'property' else 'herencia'
            facts.append(UserFact(
                fact_id=self._generate_fact_id('donation_type', donation_type),
                fact_type='donation_type',
                content=f"El tipo de donation es: {type_label}",
                confidence=0.85,
                source='user_statement'
            ))
        
        # Extract donor relation
        donor_relation = self._extract_donor_relation(message)
        if donor_relation:
            relation_label = {
                'mother': 'madre', 'father': 'padre', 
                'grandmother': 'abuela', 'grandfather': 'abuelo',
                'partner': 'pareja/cónyuge'
            }.get(donor_relation, donor_relation)
            facts.append(UserFact(
                fact_id=self._generate_fact_id('donor_relation', donor_relation),
                fact_type='donor_relation',
                content=f"El donante es: {relation_label}",
                confidence=0.9,
                source='user_statement'
            ))
        
        return facts
    
    def _generate_fact_id(self, fact_type: str, content_key: str) -> str:
        """Generate unique ID for a fact."""
        return f"{fact_type}_{hashlib.md5(content_key.encode()).hexdigest()[:8]}"
    
    # ========================================
    # VECTOR MEMORY OPERATIONS
    # ========================================
    
    async def store_fact(self, user_id: str, fact: UserFact) -> bool:
        """
        Store a fact in vector memory.
        
        Args:
            user_id: User ID
            fact: UserFact to store
            
        Returns:
            True if successful
        """
        if not self._vector_index:
            logger.debug("Vector index not available, skipping fact storage")
            return False
        
        try:
            # Generate embedding locally with OpenAI
            embedding = self._get_embedding(fact.content)
            if not embedding:
                logger.warning(f"⚠️ Could not generate embedding for fact: {fact.fact_type}")
                return False
            
            vector_id = f"{user_id}_{fact.fact_id}"
            
            self._vector_index.upsert(
                vectors=[{
                    "id": vector_id,
                    "vector": embedding,
                    "metadata": {
                        "user_id": user_id,
                        "fact_type": fact.fact_type,
                        "content": fact.content,
                        "confidence": fact.confidence,
                        "source": fact.source,
                        "created_at": fact.created_at,
                        "last_accessed": fact.last_accessed
                    }
                }]
            )
            
            logger.info(f"💾 Stored fact for user {user_id}: {fact.fact_type}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to store fact in vector memory: {e}")
            return False
    
    async def recall_facts(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[UserFact]:
        """
        Recall relevant facts for a user based on query.
        
        Args:
            user_id: User ID
            query: Query to match against stored facts
            limit: Maximum number of facts to return
            
        Returns:
            List of relevant UserFact objects
        """
        if not self._vector_index:
            return []
        
        try:
            # Generate embedding locally with OpenAI
            query_embedding = self._get_embedding(query)
            if not query_embedding:
                logger.warning("⚠️ Could not generate embedding for recall query")
                return []
            
            # Query vector store for user's facts
            results = self._vector_index.query(
                vector=query_embedding,
                top_k=limit,
                include_metadata=True,
                filter=f"user_id = '{user_id}'"  # Filter by user
            )
            
            facts = []
            for result in results:
                fact = UserFact(
                    fact_id=result.id.split('_')[-1],
                    fact_type=result.metadata.get('fact_type', 'unknown'),
                    content=result.metadata.get('content', ''),
                    confidence=result.score,
                    source=result.metadata.get('source', 'unknown'),
                    created_at=result.metadata.get('created_at', ''),
                    last_accessed=datetime.utcnow().isoformat()
                )
                facts.append(fact)
            
            logger.info(f"🔍 Recalled {len(facts)} facts for user {user_id}")
            return facts
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to recall facts: {e}")
            return []
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get all stored context for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with user's stored context
        """
        context = {
            "profile": None,
            "facts": [],
            "ccaa": None,
            "employment": None,
            # NEW: Extended fiscal profile fields
            "edad": None,
            "ingresos_brutos": None,
            "donation_pending": None,
            "donation_type": None,
            "donation_from": None
        }
        
        # Get structured profile from DB
        if self.db:
            profile = await self._get_profile_from_db(user_id)
            if profile:
                context["profile"] = profile
                context["ccaa"] = profile.get("ccaa_residencia")
                context["employment"] = profile.get("situacion_laboral")
                
                # Extract datos_fiscales JSON fields (supports both legacy plain values and new {value, _source} format)
                datos_fiscales_raw = profile.get('datos_fiscales')
                if datos_fiscales_raw:
                    try:
                        datos_fiscales = json.loads(datos_fiscales_raw) if isinstance(datos_fiscales_raw, str) else datos_fiscales_raw
                        for df_key in ('edad', 'ingresos_brutos', 'donation_pending', 'donation_type', 'donation_from'):
                            entry = datos_fiscales.get(df_key)
                            if entry is None:
                                continue
                            # New format: {"value": ..., "_source": ...}
                            if isinstance(entry, dict) and "value" in entry:
                                context[df_key] = entry["value"]
                            else:
                                # Legacy plain value
                                context[df_key] = entry
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        # Get semantic facts from vector store
        if self._vector_index:
            # Use a general query to get all facts
            facts = await self.recall_facts(user_id, "información del usuario", limit=10)
            context["facts"] = [f.content for f in facts]
            
            # Extract CCAA from facts if not in profile
            if not context["ccaa"]:
                for fact in facts:
                    if fact.fact_type == 'residence':
                        # Extract CCAA from content
                        for ccaa in self.CCAA_MAPPING.values():
                            if ccaa in fact.content:
                                context["ccaa"] = ccaa
                                break
            
            # NEW: Extract numeric facts from vector store if not in profile
            if not context.get("edad"):
                for fact in facts:
                    if fact.fact_type == 'age':
                        import re
                        match = re.search(r'(\d+)', fact.content)
                        if match:
                            context["edad"] = int(match.group(1))
                            break
            
            if not context.get("ingresos_brutos"):
                for fact in facts:
                    if fact.fact_type == 'income':
                        import re
                        match = re.search(r'(\d+)', fact.content)
                        if match:
                            context["ingresos_brutos"] = int(match.group(1))
                            break
            
            if not context.get("donation_pending"):
                for fact in facts:
                    if fact.fact_type == 'donation_amount':
                        import re
                        match = re.search(r'(\d+)', fact.content)
                        if match:
                            context["donation_pending"] = int(match.group(1))
                            break
        
        return context
    
    # ========================================
    # DATABASE OPERATIONS
    # ========================================
    
    async def _get_profile_from_db(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from Turso database."""
        if not self.db:
            return None
        
        try:
            result = await self.db.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?",
                [user_id]
            )
            
            if result.rows:
                return dict(result.rows[0])
            return None
            
        except Exception as e:
            logger.debug(f"Profile not found for user {user_id}: {e}")
            return None
    
    async def _update_datos_fiscales(
        self,
        user_id: str,
        key: str,
        value: Any,
        source: str = "conversation"
    ) -> bool:
        """
        Update a field in datos_fiscales JSON column with source tracking.

        Fields with _source="manual" are NOT overwritten by conversation data.

        Args:
            user_id: User ID
            key: Field key to update
            value: Value to store
            source: Origin of the data ("conversation" or "manual")

        Returns:
            True if successful
        """
        if not self.db:
            return False

        try:
            # Get current profile
            profile = await self._get_profile_from_db(user_id)

            # Get current datos_fiscales or create new
            datos_fiscales = {}
            if profile and profile.get('datos_fiscales'):
                try:
                    datos_fiscales = json.loads(profile['datos_fiscales'])
                except (json.JSONDecodeError, TypeError):
                    datos_fiscales = {}

            # Check source priority: manual > conversation
            existing_entry = datos_fiscales.get(key)
            if (
                isinstance(existing_entry, dict)
                and existing_entry.get("_source") == "manual"
                and source == "conversation"
            ):
                logger.debug(
                    "Skipping update for %s: manual data has priority over conversation",
                    key,
                )
                return False

            # Update the field with source metadata
            now = datetime.utcnow().isoformat()
            datos_fiscales[key] = {
                "value": value,
                "_source": source,
                "_updated": now,
            }
            datos_fiscales_json = json.dumps(datos_fiscales)

            if profile:
                # Update existing
                await self.db.execute(
                    "UPDATE user_profiles SET datos_fiscales = ?, updated_at = ? WHERE user_id = ?",
                    [datos_fiscales_json, now, user_id]
                )
            else:
                # Create new profile
                import uuid
                profile_id = str(uuid.uuid4())
                await self.db.execute(
                    """INSERT INTO user_profiles
                       (id, user_id, datos_fiscales, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    [profile_id, user_id, datos_fiscales_json, now, now]
                )

            logger.info("Updated datos_fiscales for user %s: %s=%s (source=%s)", user_id, key, value, source)
            return True

        except Exception as e:
            logger.error(f"Failed to update datos_fiscales: {e}")
            return False
    
    async def update_profile(
        self,
        user_id: str,
        ccaa: Optional[str] = None,
        employment: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Update user profile in database.
        
        Args:
            user_id: User ID
            ccaa: CCAA of residence
            employment: Employment situation
            **kwargs: Additional profile fields
            
        Returns:
            True if successful
        """
        if not self.db:
            logger.warning("Database not available for profile update")
            return False
        
        try:
            now = datetime.utcnow().isoformat()
            
            # Check if profile exists
            existing = await self._get_profile_from_db(user_id)
            
            if existing:
                # Update existing profile
                update_fields = ["updated_at = ?"]
                params = [now]
                
                if ccaa:
                    update_fields.append("ccaa_residencia = ?")
                    params.append(ccaa)
                if employment:
                    update_fields.append("situacion_laboral = ?")
                    params.append(employment)
                
                params.append(user_id)
                
                await self.db.execute(
                    f"UPDATE user_profiles SET {', '.join(update_fields)} WHERE user_id = ?",
                    params
                )
            else:
                # Create new profile
                import uuid
                profile_id = str(uuid.uuid4())
                
                await self.db.execute(
                    """INSERT INTO user_profiles 
                       (id, user_id, ccaa_residencia, situacion_laboral, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    [profile_id, user_id, ccaa, employment, now, now]
                )
            
            logger.info(f"✅ Updated profile for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update profile: {e}")
            return False
    
    async def process_message_for_memory(
        self,
        user_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Process a user message to extract and store facts.
        
        This is the main entry point for memory extraction.
        
        Args:
            user_id: User ID
            message: User's message
            
        Returns:
            Dict with extracted facts and updated context
        """
        # Extract facts from message
        facts = self.extract_facts_from_message(message)
        
        # Store facts in vector memory
        for fact in facts:
            await self.store_fact(user_id, fact)
        
        # Update structured profile if we found residence or employment
        for fact in facts:
            if fact.fact_type == 'residence':
                # Extract CCAA and update profile
                for city, ccaa in self.CCAA_MAPPING.items():
                    if city in message.lower():
                        await self.update_profile(user_id, ccaa=ccaa)
                        break
            elif fact.fact_type == 'employment':
                if 'autónomo' in fact.content:
                    await self.update_profile(user_id, employment='autonomo')
                elif 'asalariado' in fact.content:
                    await self.update_profile(user_id, employment='asalariado')
                elif 'pensionista' in fact.content:
                    await self.update_profile(user_id, employment='pensionista')
            # NEW: Update profile with numeric values
            elif fact.fact_type == 'age':
                # Extract age from content
                import re
                age_match = re.search(r'(\d+)', fact.content)
                if age_match:
                    age = int(age_match.group(1))
                    # Store in datos_fiscales JSON
                    await self._update_datos_fiscales(user_id, 'edad', age)
            elif fact.fact_type == 'income':
                import re
                income_match = re.search(r'(\d+)', fact.content)
                if income_match:
                    income = int(income_match.group(1))
                    await self._update_datos_fiscales(user_id, 'ingresos_brutos', income)
            elif fact.fact_type == 'donation_amount':
                import re
                amount_match = re.search(r'(\d+)', fact.content)
                if amount_match:
                    amount = int(amount_match.group(1))
                    await self._update_datos_fiscales(user_id, 'donation_pending', amount)
            elif fact.fact_type == 'donation_type':
                # Extract donation type
                if 'dinero' in fact.content:
                    await self._update_datos_fiscales(user_id, 'donation_type', 'money')
                elif 'vivienda' in fact.content or 'inmueble' in fact.content:
                    await self._update_datos_fiscales(user_id, 'donation_type', 'property')
                elif 'herencia' in fact.content:
                    await self._update_datos_fiscales(user_id, 'donation_type', 'inheritance')
            elif fact.fact_type == 'donor_relation':
                # Extract donor relation
                if 'madre' in fact.content:
                    await self._update_datos_fiscales(user_id, 'donation_from', 'mother')
                elif 'padre' in fact.content:
                    await self._update_datos_fiscales(user_id, 'donation_from', 'father')
                elif 'abuela' in fact.content:
                    await self._update_datos_fiscales(user_id, 'donation_from', 'grandmother')
                elif 'abuelo' in fact.content:
                    await self._update_datos_fiscales(user_id, 'donation_from', 'grandfather')
                elif 'pareja' in fact.content or 'cónyuge' in fact.content:
                    await self._update_datos_fiscales(user_id, 'donation_from', 'partner')
        
        # Get updated context
        context = await self.get_user_context(user_id)
        
        return {
            "extracted_facts": len(facts),
            "facts": [f.content for f in facts],
            "context": context
        }


# Global instance
_user_memory_service: Optional[UserMemoryService] = None


def get_user_memory_service(db_client=None) -> UserMemoryService:
    """Get global User Memory Service instance."""
    global _user_memory_service
    if _user_memory_service is None:
        _user_memory_service = UserMemoryService(db_client=db_client)
    elif db_client and _user_memory_service.db is None:
        _user_memory_service.db = db_client
    return _user_memory_service
