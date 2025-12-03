# src/rag_engine.py
import os
import re
import uuid
import hashlib
import pickle
import logging
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Dict, Any

import numpy as np
import pandas as pd
import faiss
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

# Reranker opcional
try:
    from sentence_transformers import CrossEncoder
    _HAS_CE = True
except Exception:
    CrossEncoder = None
    _HAS_CE = False

from openai import OpenAI

# ---------------------------------------------------------------------
# SETTINGS: import desde app.config + SHIM de compatibilidad nombres
# ---------------------------------------------------------------------
from app.config import settings as _raw_settings


class _SettingsShim:
    """
    Permite acceder a settings.* en minúsculas aunque tu config esté en MAYÚSCULAS
    y hace mapeos de nombres comunes.
    """
    _map = {
        "pdf_dir": "INDEX_DIR",
        "cache_dir": "CACHE_DIR",
        "parquet_path": "PARQUET_PATH",
        "meta_path": "META_PATH",
        "index_path": "INDEX_PATH",
        "embedding_model": "EMB_MODEL_NAME",
        "reranking_model": "RERANKING_MODEL",
        "openai_model": "OPENAI_MODEL",
        "openai_api_key": "OPENAI_API_KEY",
        "temperature": "TEMPERATURE",
        "max_tokens": "MAX_TOKENS",
        "retrieval_k": "RETRIEVAL_K",
        "rerank_k": "RERANK_K",
    }

    def __init__(self, s):
        self._s = s

    def __getattr__(self, name):
        # 1) tal cual
        if hasattr(self._s, name):
            return getattr(self._s, name)
        # 2) MAYÚSCULAS
        up = name.upper()
        if hasattr(self._s, up):
            return getattr(self._s, up)
        # 3) mapeo
        if name in self._map and hasattr(self._s, self._map[name]):
            return getattr(self._s, self._map[name])
        raise AttributeError(name)


settings = _SettingsShim(_raw_settings)

# ---------------------------------------------------------------------
# GUARDRails: importa de src/taxia_guardrails con fallback stub
# ---------------------------------------------------------------------
try:
    from src.taxia_guardrails import guardrails_system, GuardResult
except Exception:
    class GuardResult:
        def __init__(self, passed=True, content=None, violations=None):
            self.passed = passed
            self.content = content
            self.violations = violations or []

    class _StubGuardrails:
        def validate_input(self, q): return GuardResult(True, q, [])
        def validate_output(self, a, ctx): return GuardResult(True, a, [])

    guardrails_system = _StubGuardrails()

# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------
logger = logging.getLogger("rag_engine")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------
# DATASTRUCTS
# ---------------------------------------------------------------------
@dataclass
class Chunk:
    """Estructura de chunk con metadatos adicionales"""
    id: str
    source: str
    page: int
    title: str
    section_path: str
    text: str
    word_count: int = 0
    char_count: int = 0

    def __post_init__(self):
        self.word_count = len((self.text or "").split())
        self.char_count = len(self.text or "")


@dataclass
class RetrievalResult:
    """Resultado de recuperación con scores"""
    chunks: List[Chunk]
    similarity_scores: List[float]
    rerank_scores: Optional[List[float]] = None
    query: str = ""
    retrieval_time: float = 0.0
    rerank_time: float = 0.0


# ---------------------------------------------------------------------
# CACHE
# ---------------------------------------------------------------------
class CacheManager:
    """Gestor de caché para embeddings y respuestas"""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.embeddings_cache_path = os.path.join(cache_dir, "embeddings_cache.pkl")
        self.responses_cache_path = os.path.join(cache_dir, "responses_cache.pkl")
        self.embeddings_cache = self._load_cache(self.embeddings_cache_path)
        self.responses_cache = self._load_cache(self.responses_cache_path)

    def _load_cache(self, path: str) -> Dict:
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Error cargando caché {path}: {e}")
        return {}

    def _save_cache(self, cache_data: Dict, path: str):
        try:
            with open(path, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.error(f"Error guardando caché {path}: {e}")

    def get_embedding_cache_key(self, text: str, model_name: str) -> str:
        content = f"{text}:{model_name}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_response_cache_key(self, query: str, context_chunks: List[str]) -> str:
        context_text = "|".join(context_chunks)
        content = f"{query}:{context_text}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_cached_embedding(self, text: str, model_name: str) -> Optional[np.ndarray]:
        key = self.get_embedding_cache_key(text, model_name)
        return self.embeddings_cache.get(key)

    def cache_embedding(self, text: str, model_name: str, embedding: np.ndarray):
        key = self.get_embedding_cache_key(text, model_name)
        self.embeddings_cache[key] = embedding
        if len(self.embeddings_cache) % 100 == 0:
            self._save_cache(self.embeddings_cache, self.embeddings_cache_path)

    def get_cached_response(self, query: str, context_chunks: List[str]) -> Optional[str]:
        key = self.get_response_cache_key(query, context_chunks)
        return self.responses_cache.get(key)

    def cache_response(self, query: str, context_chunks: List[str], response: str):
        key = self.get_response_cache_key(query, context_chunks)
        self.responses_cache[key] = response
        if len(self.responses_cache) % 50 == 0:
            self._save_cache(self.responses_cache, self.responses_cache_path)

    def save_all_caches(self):
        self._save_cache(self.embeddings_cache, self.embeddings_cache_path)
        self._save_cache(self.responses_cache, self.responses_cache_path)


# ---------------------------------------------------------------------
# DOCUMENTS
# ---------------------------------------------------------------------
class DocumentProcessor:
    """Procesador de documentos PDF con split semántico"""

    def __init__(self):
        self.cache_manager = CacheManager(settings.cache_dir)

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        text = (text.replace('–', '-').replace('—', '-')
                .replace('’', "'").replace('‘', "'")
                .replace('“', '"').replace('”', '"'))
        return text.strip()

    def _extract_title(self, page_text: str) -> str:
        patterns = [
            r'(?m)^(Cap[ií]tulo\s+\d+[^\n]{0,80})$',
            r'(?m)^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,80})$',
            r'(?m)^(\d+\.\s*[A-ZÁÉÍÓÚÑ][^\n]{5,80})$',
            r'(?m)^([A-ZÁÉÍÓÚÑ][^\n]{10,80})\s*$'
        ]
        for pat in patterns:
            m = re.search(pat, page_text)
            if m:
                t = m.group(1).strip()
                if not re.match(r'^[A-Z\d\s]+$', t):
                    return t
        # fallback
        for line in page_text.strip().split('\n'):
            clean = self._clean_text(line)
            if 10 < len(clean) < 100:
                return clean
        return ""

    def _smart_text_splitting(self, text: str,
                              max_chars: Optional[int] = None,
                              overlap: Optional[int] = None) -> List[str]:
        max_chars = max_chars or settings.chunk_size
        overlap = overlap or settings.chunk_overlap
        text = (text or "").strip()
        if not text:
            return []
        if len(text) <= max_chars:
            return [text]

        chunks, start, n = [], 0, len(text)
        while start < n:
            end = min(n, start + max_chars)
            sub = text[start:end]
            best_cut = end - start
            cut_points = [r'\.\s+[A-ZÁÉÍÓÚÑ]', r';\s+', r':\s+', r',\s+', r'\s+']
            for pat in cut_points:
                matches = list(re.finditer(pat, sub))
                if matches:
                    min_size = int(len(sub) * 0.4)
                    for m in reversed(matches):
                        if m.end() >= min_size:
                            best_cut = m.end()
                            break
                    break
            piece = text[start:start + best_cut].strip()
            if len(piece) > 100:
                chunks.append(piece)
            start = max(start + best_cut - overlap, start + best_cut)
        return chunks

    def ingest_documents(self, pdf_dir: str) -> pd.DataFrame:
        logger.info(f"Iniciando ingesta desde {pdf_dir}")
        rows, processed = [], 0
        if not os.path.isdir(pdf_dir):
            raise FileNotFoundError(f"No existe la carpeta de PDFs: {pdf_dir}")
        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
        logger.info(f"Encontrados {len(pdf_files)} archivos PDF")
        for fname in pdf_files:
            path = os.path.join(pdf_dir, fname)
            try:
                logger.info(f"Procesando: {fname}")
                reader = PdfReader(path)
                for page_num, page in enumerate(reader.pages, start=1):
                    try:
                        raw = page.extract_text()
                        clean = self._clean_text(raw)
                        if not clean or len(clean) < 50:
                            continue
                        title = self._extract_title(clean)
                        parts = self._smart_text_splitting(clean)
                        for txt in parts:
                            chunk = Chunk(
                                id=str(uuid.uuid4()),
                                source=fname,
                                page=page_num,
                                title=title,
                                section_path=title,
                                text=txt
                            )
                            rows.append(asdict(chunk))
                    except Exception as e:
                        logger.warning(f"Error página {page_num} de {fname}: {e}")
                processed += 1
                logger.info(f"✓ {fname}: {len([r for r in rows if r['source'] == fname])} chunks")
            except Exception as e:
                logger.error(f"Error archivo {fname}: {e}")
        df = pd.DataFrame(rows)
        logger.info(f"Ingesta completada: {processed} archivos, {len(df)} chunks")
        return df


# ---------------------------------------------------------------------
# RAG ENGINE
# ---------------------------------------------------------------------
class RAGEngine:
    """Motor RAG con caché, reranking y guardrails"""

    def __init__(self):
        self.settings = settings
        os.makedirs(settings.cache_dir, exist_ok=True)
        # asegurar carpetas de artefactos
        for p in [settings.parquet_path, settings.meta_path, settings.index_path]:
            d = os.path.dirname(p or "")
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)

        self.doc_processor = DocumentProcessor()
        self.cache_manager = CacheManager(settings.cache_dir)

        self.embedder: Optional[SentenceTransformer] = None
        self.reranker: Optional[CrossEncoder] = None
        self.openai_client: Optional[OpenAI] = None

        self.df: Optional[pd.DataFrame] = None
        self.index: Optional[faiss.Index] = None
        self.is_initialized: bool = False

    # ----------------- Artefactos y compatibilidad -----------------
    def _artifact_candidates(self) -> dict:
        """Posibles ubicaciones de artefactos (config y raíz del repo)."""
        # actuales (según settings)
        p_parquet = settings.parquet_path
        p_index = settings.index_path
        p_meta = settings.meta_path
        meta_json = os.path.join(os.path.dirname(p_index) or ".", "aeat_artifacts.json")

        # alternativas (compat con artefactos antiguos en raíz del proyecto)
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        alt_parquet = os.path.join(root_dir, "aeat_corpus.parquet")
        alt_index = os.path.join(root_dir, "aeat_faiss.index")
        alt_meta = os.path.join(root_dir, "aeat_meta.parquet")
        alt_json = os.path.join(root_dir, "aeat_artifacts.json")

        return {
            "parquet": [p_parquet, alt_parquet],
            "index": [p_index, alt_index],
            "meta": [p_meta, alt_meta],
            "metajson": [meta_json, alt_json],
        }

    def _pick_first_existing(self, paths: List[str]) -> Optional[str]:
        for p in paths:
            if p and os.path.exists(p):
                return p
        return None

    def _fingerprint_df(self, df: pd.DataFrame) -> str:
        """Huella estable del corpus para detectar cambios sin reindexar entero."""
        cols = [c for c in ["id", "source", "page", "char_count"] if c in df.columns]
        if not cols:
            tmp = df.copy()
            tmp["__len"] = tmp["text"].astype(str).str.len()
            cols = ["__len"]
            material = tmp[cols].to_string(index=False)
        else:
            material = df[cols].to_string(index=False)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _write_artifacts_meta(self, df: pd.DataFrame, meta_path: str):
        meta = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "embedding_model": settings.embedding_model,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "retrieval_k": settings.retrieval_k,
            "rerank_k": settings.rerank_k,
            "df_len": len(df),
            "fingerprint": self._fingerprint_df(df),
        }
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            logger.info(f"Metadatos guardados: {meta_path}")
        except Exception as e:
            logger.warning(f"No se pudo escribir metadatos: {e}")

    def _load_artifacts_meta(self, candidates: dict) -> tuple[Optional[dict], Optional[str]]:
        path = self._pick_first_existing(candidates["metajson"])
        if not path:
            return None, None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), path
        except Exception as e:
            logger.warning(f"No se pudo leer metadatos {path}: {e}")
            return None, path

    def _meta_is_compatible(self, meta: dict, df: pd.DataFrame, index_obj) -> bool:
        if not meta:
            logger.info("No hay metadatos de artefactos → posible rebuild.")
            return False
        if meta.get("embedding_model") != settings.embedding_model:
            logger.info("Cambio de modelo de embeddings → rebuild.")
            return False
        if meta.get("chunk_size") != settings.chunk_size or meta.get("chunk_overlap") != settings.chunk_overlap:
            logger.info("Cambio de chunking (size/overlap) → rebuild.")
            return False
        if meta.get("df_len") != len(df):
            logger.info(f"df_len distinto ({meta.get('df_len')} vs {len(df)}) → rebuild.")
            return False
        if index_obj.ntotal != len(df):
            logger.info(f"Índice/DF desalineados ({index_obj.ntotal} vs {len(df)}) → rebuild.")
            return False
        fp_now = self._fingerprint_df(df)
        if meta.get("fingerprint") != fp_now:
            logger.info("Fingerprint del corpus distinto → rebuild.")
            return False
        return True

    # ----------------- init / load -----------------
    def initialize(self):
        logger.info("Inicializando motor RAG...")
        try:
            logger.info(f"Embeddings: {settings.embedding_model}")
            self.embedder = SentenceTransformer(settings.embedding_model)

            rerank_model = getattr(settings, "reranking_model", None)
            if rerank_model and _HAS_CE:
                logger.info(f"Reranker: {rerank_model}")
                self.reranker = CrossEncoder(rerank_model)
            else:
                if rerank_model and not _HAS_CE:
                    logger.warning("CrossEncoder no disponible; se usará solo similitud vectorial.")
                self.reranker = None

            self.openai_client = OpenAI(api_key=settings.openai_api_key)

            if self._load_existing_data():
                logger.info("Datos existentes cargados.")
            else:
                logger.info("No hay artefactos; construyendo índice…")
                self._build_index()

            self.is_initialized = True
            logger.info("RAG listo ✔")
        except Exception as e:
            logger.error(f"Fallo inicializando RAG: {e}")
            raise

    def _load_existing_data(self) -> bool:
        """Carga artefactos si existen y son compatibles (multi-ruta + metadatos)."""
        cand = self._artifact_candidates()
        parquet_path = self._pick_first_existing(cand["parquet"])
        index_path = self._pick_first_existing(cand["index"])
        if not (parquet_path and index_path):
            return False
        try:
            df = pd.read_parquet(parquet_path)
            index_obj = faiss.read_index(index_path)
        except Exception as e:
            logger.warning(f"Error cargando artefactos: {e}")
            return False

        meta, _ = self._load_artifacts_meta(cand)
        if not self._meta_is_compatible(meta, df, index_obj):
            return False

        self.df = df
        self.index = index_obj
        logger.info(f"Cargados artefactos: {len(df)} chunks, índice {index_obj.ntotal}.")
        return True

    def _build_index(self):
        self.df = self.doc_processor.ingest_documents(settings.pdf_dir)
        if self.df.empty:
            raise ValueError("Ingesta vacía: no hay chunks")

        logger.info("Generando embeddings…")
        texts = self.df["text"].tolist()
        embs = self._get_embeddings_batch(texts)  # (N, D) float32 normalizados

        dim = embs.shape[1]
        self.index = faiss.IndexFlatIP(dim)  # producto interno (usar embs normalizados)
        self.index.add(embs)

        self.df.to_parquet(settings.parquet_path, index=False)
        faiss.write_index(self.index, settings.index_path)

        meta_df = self.df[["id", "source", "page", "title", "section_path"]].copy()
        meta_df.to_parquet(settings.meta_path, index=False)

        # Escribir metadatos de compatibilidad
        meta_json_path = os.path.join(os.path.dirname(settings.index_path) or ".", "aeat_artifacts.json")
        self._write_artifacts_meta(self.df, meta_json_path)

        logger.info(f"Índice creado: {len(self.df)} chunks")

    def _get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        out = []
        hits = 0
        for t in texts:
            cached = self.cache_manager.get_cached_embedding(t, settings.embedding_model)
            if cached is not None:
                out.append(cached)
                hits += 1
            else:
                v = self.embedder.encode([t], normalize_embeddings=True)[0]
                out.append(v)
                self.cache_manager.cache_embedding(t, settings.embedding_model, v)
        logger.info(f"Embeddings desde caché: {hits}/{len(texts)}")
        return np.asarray(out, dtype=np.float32)

    # ----------------- retrieval -----------------
    def retrieve(self, query: str, k: Optional[int] = None) -> RetrievalResult:
        import time as _time
        if not self.is_initialized:
            raise RuntimeError("RAG no inicializado; llama primero a initialize()")

        k = k or getattr(settings, "retrieval_k", 6)
        start = _time.time()

        qv = self.embedder.encode([query], normalize_embeddings=True).astype(np.float32)
        search_k = min(max(k * 3, k), len(self.df))
        sims, idxs = self.index.search(qv, search_k)
        retrieval_time = _time.time() - start

        cands: List[Chunk] = []
        simscores: List[float] = []
        for i, s in zip(idxs[0], sims[0]):
            if i >= 0:
                row = self.df.iloc[i]
                cands.append(Chunk(**row.to_dict()))
                simscores.append(float(s))

        # Reranking opcional
        rstart = _time.time()
        reranked, rerscores = self._rerank_chunks(query, cands, k)
        rerank_time = _time.time() - rstart

        final_sim = []
        for ch in reranked:
            for ii, oo in enumerate(cands):
                if oo.id == ch.id:
                    final_sim.append(simscores[ii])
                    break

        return RetrievalResult(
            chunks=reranked,
            similarity_scores=final_sim,
            rerank_scores=rerscores,
            query=query,
            retrieval_time=retrieval_time,
            rerank_time=rerank_time
        )

    def _rerank_chunks(self, query: str, chunks: List[Chunk], top_k: int) -> Tuple[List[Chunk], List[float]]:
        if len(chunks) <= top_k or not self.reranker:
            return chunks[:top_k], [1.0] * min(top_k, len(chunks))
        pairs = [(query, c.text) for c in chunks]
        try:
            scores = self.reranker.predict(pairs)  # np.array
        except Exception as e:
            logger.warning(f"Rerank falló, usando denso: {e}")
            return chunks[:top_k], [1.0] * min(top_k, len(chunks))
        order = np.argsort(scores)[::-1]
        top = order[:top_k]
        return [chunks[i] for i in top], [float(scores[i]) for i in top]

    # ----------------- generación -----------------
    def generate_response(self, query: str, k: Optional[int] = None) -> Dict[str, Any]:
        k = k or getattr(settings, "retrieval_k", 6)

        # 1) guardrails de entrada
        inp = guardrails_system.validate_input(query)
        if not inp.passed:
            return {
                "answer": inp.content,
                "sources": [],
                "guardrails_triggered": True,
                "guardrails_violations": inp.violations
            }
        safe_query = inp.content

        # 2) retrieve + caché de respuesta
        ret = self.retrieve(safe_query, k)
        ctx_texts = [c.text for c in ret.chunks]
        cached = self.cache_manager.get_cached_response(safe_query, ctx_texts)
        if cached:
            return {
                "answer": cached,
                "sources": self._format_sources(ret.chunks),
                "cached": True,
                "similarity_scores": ret.similarity_scores,
                "rerank_scores": ret.rerank_scores,
                "retrieval_time": ret.retrieval_time,
                "rerank_time": ret.rerank_time,
                "guardrails_violations": []
            }

        # 3) prompt
        prompt = self._assemble_prompt(safe_query, ret.chunks)

        # 4) LLM
        try:
            resp = self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=float(getattr(settings, "temperature", 0.2)),
                max_tokens=int(getattr(settings, "max_tokens", 1200)),
            )
            raw = resp.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raw = "Lo siento, no puedo generar una respuesta ahora mismo. Intenta de nuevo."

        # 5) guardrails de salida
        out = guardrails_system.validate_output(raw, ctx_texts)
        final_answer = out.content

        # 6) cachea si OK
        if not out.violations:
            self.cache_manager.cache_response(safe_query, ctx_texts, final_answer)

        return {
            "answer": final_answer,
            "sources": self._format_sources(ret.chunks),
            "similarity_scores": ret.similarity_scores,
            "rerank_scores": ret.rerank_scores,
            "retrieval_time": ret.retrieval_time,
            "rerank_time": ret.rerank_time,
            "guardrails_violations": inp.violations + out.violations,
            "cached": False
        }

    def _assemble_prompt(self, query: str, chunks: List[Chunk]) -> str:
        ctx = []
        for i, c in enumerate(chunks):
            ctx.append(f"[{i}] ({c.source} p.{c.page}) {c.text}")
        context = "\n\n".join(ctx)
        return (
            "Usa EXCLUSIVAMENTE los fragmentos del CONTEXTO para responder.\n"
            "No inventes artículos, modelos ni conclusiones no respaldadas.\n\n"
            f"Pregunta del usuario: {query}\n\n"
            f"CONTEXTO:\n{context}\n\n"
            "FORMATO DE SALIDA OBLIGATORIO:\n"
            "**Veredicto corto:** <SÍ/No/Depende + 1 frase>\n"
            "**Resumen entendible:** 2-4 líneas, sin jerga.\n"
            "**Por qué:** puntos claros (3-5 bullets).\n"
            "**Modelos/Formularios (si aplica):** Enumera SOLO los modelos que aparezcan en el contexto.\n"
            "**Qué debes comprobar o aportar:** bullets con datos faltantes (si hay).\n"
            "**Ejemplo rápido (opcional):** 1 ejemplo con números sencillos si procede.\n"
            "**Citas (mín. 2):** - Documento, página (p.X)\n"
            "**Aviso:** Esto no constituye asesoramiento profesional. Verifícalo con tu asesor.\n\n"
            "Responde ahora:"
        )

    def _get_system_prompt(self) -> str:
        return (
            "Eres un asistente fiscal para ciudadanos y pymes en España. "
            "Respondes en español claro, directo y sin jerga. "
            "Primero das un veredicto corto (Sí/No/Depende) y luego explicas en lenguaje sencillo. "
            "Incluyes ejemplos numéricos cuando ayudan. "
            "SIEMPRE devuelves citaciones (doc y página) y un aviso legal. "
            "Si faltan datos (año, CCAA, régimen, importes), los pides antes de concluir. "
            "Cuando una petición sea ilegal o pida evadir impuestos, te niegas y ofreces alternativas legales. "
            "No inventes artículos ni modelos si no aparecen en el contexto RAG."
        )

    def _format_sources(self, chunks: List[Chunk]) -> List[Dict[str, Any]]:
        out = []
        for c in chunks:
            out.append({
                "id": c.id,
                "source": c.source,
                "page": c.page,
                "title": c.title,
                "text_preview": (c.text[:200] + "...") if len(c.text) > 200 else c.text
            })
        return out

    # ----------------- mantenimiento -----------------
    def rebuild_index(self, pdf_dir: Optional[str] = None):
        pdf_dir = pdf_dir or settings.pdf_dir
        logger.info(f"Reconstruyendo índice desde {pdf_dir}")
        self.df = None
        self.index = None
        self._build_index()
        self.is_initialized = True
        logger.info("Índice reconstruido ✔")

    def get_statistics(self) -> Dict[str, Any]:
        if not self.is_initialized:
            return {"error": "RAG no inicializado"}
        avg_len = self.df["char_count"].mean() if "char_count" in self.df.columns else 0
        return {
            "total_chunks": len(self.df),
            "total_sources": self.df["source"].nunique(),
            "avg_chunk_length": float(avg_len),
            "index_size": self.index.ntotal if self.index else 0,
            "embedding_model": settings.embedding_model,
            "reranking_model": getattr(settings, "reranking_model", None),
            "cache_stats": {
                "embeddings_cached": len(self.cache_manager.embeddings_cache),
                "responses_cached": len(self.cache_manager.responses_cache),
            },
        }


# Instancia global
rag_engine = RAGEngine()