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
        
        # Initialize vector index if available
        if UPSTASH_VECTOR_AVAILABLE and self.vector_url and self.vector_token:
            try:
                self._vector_index = Index(url=self.vector_url, token=self.vector_token)
                logger.info("🧠 User Memory Service initialized with Upstash Vector")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Upstash Vector for user memory: {e}")
        else:
            logger.info("📝 User Memory Service initialized (DB only mode)")
    
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
            vector_id = f"{user_id}_{fact.fact_id}"
            
            self._vector_index.upsert(
                vectors=[{
                    "id": vector_id,
                    "data": fact.content,
                    "metadata": {
                        "user_id": user_id,
                        "fact_type": fact.fact_type,
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
            # Query vector store for user's facts
            results = self._vector_index.query(
                data=query,
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
            "employment": None
        }
        
        # Get structured profile from DB
        if self.db:
            profile = await self._get_profile_from_db(user_id)
            if profile:
                context["profile"] = profile
                context["ccaa"] = profile.get("ccaa_residencia")
                context["employment"] = profile.get("situacion_laboral")
        
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
