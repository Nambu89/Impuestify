"""
Rate Limiter and DDoS Protection for TaxIA

Multi-layer protection against abuse:
1. Per-endpoint rate limiting (SlowAPI) with CORS support
2. IP-based automatic blocking
3. Attack pattern detection
4. Structured logging for monitoring

Uses in-memory storage (upgradeble to Redis for distributed setups).
"""
import os
import time
import logging
from typing import Callable, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


# === IP Blocking System ===

class IPBlocker:
	"""
	Automatic IP blocking after repeated rate limit violations.
	
	Blocks IPs that violate rate limits too many times in a time window.
	"""
	
	def __init__(
		self,
		max_violations: int = 5,
		block_duration_minutes: int = 60,
		violation_window_minutes: int = 10
	):
		"""
		Initialize IP blocker.
		
		Args:
			max_violations: Max violations before blocking
			block_duration_minutes: How long to block IP
			violation_window_minutes: Time window to count violations
		"""
		self.max_violations = max_violations
		self.block_duration = timedelta(minutes=block_duration_minutes)
		self.violation_window = timedelta(minutes=violation_window_minutes)
		
		# Track violations: {ip: [(timestamp, endpoint), ...]}
		self.violations: Dict[str, list] = defaultdict(list)
		
		# Blocked IPs: {ip: block_until_timestamp}
		self.blocked_ips: Dict[str, datetime] = {}
	
	def record_violation(self, ip: str, endpoint: str):
		"""Record a rate limit violation."""
		now = datetime.now()
		
		# Clean old violations (outside time window)
		self.violations[ip] = [
			(ts, ep) for ts, ep in self.violations[ip]
			if now - ts < self.violation_window
		]
		
		# Add new violation
		self.violations[ip].append((now, endpoint))
		
		# Check if should block
		if len(self.violations[ip]) >= self.max_violations:
			block_until = now + self.block_duration
			self.blocked_ips[ip] = block_until
			logger.warning(
				f"🚨 IP BLOCKED: {ip} - {len(self.violations[ip])} violations "
				f"in {self.violation_window.total_seconds() / 60:.0f}min. "
				f"Blocked until {block_until.isoformat()}"
			)
			return True
		
		return False
	
	def is_blocked(self, ip: str) -> bool:
		"""Check if IP is currently blocked."""
		if ip not in self.blocked_ips:
			return False
		
		block_until = self.blocked_ips[ip]
		now = datetime.now()
		
		if now >= block_until:
			# Block expired, remove
			del self.blocked_ips[ip]
			logger.info(f"✅ IP UNBLOCKED: {ip}")
			return False
		
		return True
	
	def get_block_remaining_seconds(self, ip: str) -> Optional[int]:
		"""Get remaining seconds of block for IP."""
		if ip not in self.blocked_ips:
			return None
		
		remaining = (self.blocked_ips[ip] - datetime.now()).total_seconds()
		return max(0, int(remaining))
	
	def get_stats(self) -> dict:
		"""Get blocker statistics."""
		return {
			"total_blocked_ips": len(self.blocked_ips),
			"blocked_ips": list(self.blocked_ips.keys()),
			"violation_counts": {
				ip: len(violations)
				for ip, violations in self.violations.items()
				if violations  # Only show IPs with current violations
			}
		}


# Global IP blocker instance
ip_blocker = IPBlocker(
	max_violations=5,      # Block after 5 violations
	block_duration_minutes=60,  # Block for 1 hour
	violation_window_minutes=10  # Count violations in 10-minute window
)


# === Rate Limit Key Function ===

def get_rate_limit_key(request: Request) -> str:
	"""
	Get rate limit key based on user identity.
	
	Uses JWT user ID if authenticated, otherwise falls back to IP address.
	"""
	# Try to get user from JWT token
	auth_header = request.headers.get("Authorization", "")
	if auth_header.startswith("Bearer "):
		# If authenticated, could extract user ID from token
		# For now, use a hash of the token
		import hashlib
		token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:16]
		return f"user:{token_hash}"
	
	# Fallback to IP address
	return get_remote_address(request)


# === Initialize Limiter with Redis (Distributed) ===

# Try to import upstash-redis for distributed rate limiting
try:
	from upstash_redis import Redis
	UPSTASH_AVAILABLE = True
except ImportError:
	UPSTASH_AVAILABLE = False
	logger.debug("upstash-redis not available, using in-memory rate limiting")


class UpstashStorage:
	"""
	Custom storage backend for SlowAPI using Upstash Redis REST API.
	
	Provides distributed rate limiting across multiple server instances.
	"""
	
	def __init__(self, redis_client: 'Redis'):
		self.redis = redis_client
	
	def incr(self, key: str, expiry: int, elastic_expiry: bool = False) -> int:
		"""Increment a counter and set expiry."""
		try:
			# Use Redis INCR command
			count = self.redis.incr(key)
			
			# Set expiry on first increment
			if count == 1:
				self.redis.expire(key, expiry)
			
			return count
		except Exception as e:
			logger.warning(f"⚠️ Redis incr failed: {e}")
			return 0
	
	def get(self, key: str) -> int:
		"""Get current counter value."""
		try:
			value = self.redis.get(key)
			# SlowAPI expects the value to support .decode() if it's bytes (standard Redis)
			# But Upstash Redis python client returns int or str directly
			# We return it as is, but if SlowAPI tries to call .decode() on it later,
			# it might fail if we don't wrap it or if SlowAPI isn't flexible.
			# HOWEVER, the error 'UpstashStorage' object has no attribute 'decode' 
			# suggests SlowAPI might be treating the storage object itself as the connection/value?
			# No, typically it means SlowAPI tries to decode the result of get().
			
			if value is None:
				return 0
			return int(value)
		except Exception as e:
			logger.error(f"Error getting key {key} from Upstash: {e}")
			return 0
	
	def get_expiry(self, key: str) -> int:
		"""Get remaining time to live in seconds."""
		try:
			return self.redis.ttl(key)
		except Exception as e:
			logger.error(f"Error getting expiry for {key}: {e}")
			return 0


def _initialize_limiter():
	"""
	Initialize rate limiter with Redis or fallback to memory.
	
	Returns:
		Limiter instance configured with appropriate storage
	"""
	import os
	
	redis_url = os.environ.get("UPSTASH_REDIS_REST_URL")
	redis_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
	
	# Try to use Upstash Redis for distributed rate limiting
	if UPSTASH_AVAILABLE and redis_url and redis_token:
		try:
			redis_client = Redis(url=redis_url, token=redis_token)
			
			# Test connection
			redis_client.ping()
			
			storage = UpstashStorage(redis_client)
			logger.info("🚦 Rate Limiter: Using Upstash Redis (distributed)")
			
			return Limiter(
				key_func=get_rate_limit_key,
				default_limits=["100/hour", "10/minute"],
				storage_uri=storage,  # Use custom storage
				strategy="fixed-window"
			)
		except Exception as e:
			logger.warning(f"⚠️ Failed to connect to Upstash Redis: {e}. Falling back to memory.")
	
	# Fallback to in-memory storage
	logger.info("🚦 Rate Limiter: Using in-memory storage (single instance)")
	return Limiter(
		key_func=get_rate_limit_key,
		default_limits=["100/hour", "10/minute"],
		storage_uri="memory://",
		strategy="fixed-window"
	)


# Initialize limiter
limiter = _initialize_limiter()


# === Rate Limit Handler ===

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
	"""
	Custom handler for rate limit exceeded errors.
	
	Records violation and potentially blocks IP.
	"""
	ip = get_remote_address(request)
	endpoint = request.url.path
	
	# Record violation
	was_blocked = ip_blocker.record_violation(ip, endpoint)
	
	# Log with structured data
	logger.warning(
		f"⚠️ Rate limit exceeded",
		extra={
			"ip": ip,
			"endpoint": endpoint,
			"detail": str(exc.detail),
			"blocked": was_blocked
		}
	)
	
	# Get retry time
	retry_after = getattr(exc, "retry_after", 60)
	
	# If IP is now blocked, inform user
	if was_blocked:
		block_remaining = ip_blocker.get_block_remaining_seconds(ip)
		return JSONResponse(
			status_code=429,
			content={
				"error": "ip_blocked",
				"message": "Tu IP ha sido bloqueada temporalmente por exceso de solicitudes.",
				"blocked_until_seconds": block_remaining,
				"detail": "Repeated rate limit violations"
			},
			headers={
				"Retry-After": str(block_remaining),
				"X-RateLimit-Limit": "0",
				"X-RateLimit-Remaining": "0"
			}
		)
	
	return JSONResponse(
		status_code=429,
		content={
			"error": "rate_limit_exceeded",
			"message": "Has superado el límite de consultas. Por favor, espera un momento antes de intentar de nuevo.",
			"detail": str(exc.detail),
			"retry_after": retry_after
		},
		headers={
			"Retry-After": str(retry_after),
			"X-RateLimit-Limit": "10",
			"X-RateLimit-Remaining": "0"
		}
	)


# === Middleware for IP Blocking Check ===

async def check_ip_blocked(request: Request, call_next):
	"""
	Middleware to check if IP is blocked before processing request.
	
	IMPORTANT: Allows OPTIONS requests to pass through for CORS.
	"""
	# Always allow OPTIONS (CORS preflight) - NO RATE LIMITING
	if request.method == "OPTIONS":
		return await call_next(request)
	
	ip = get_remote_address(request)
	
	if ip_blocker.is_blocked(ip):
		remaining = ip_blocker.get_block_remaining_seconds(ip)
		logger.warning(f"🚫 Blocked IP attempted request: {ip} on {request.url.path}")
		
		return JSONResponse(
			status_code=403,
			content={
				"error": "ip_blocked",
				"message": "Tu IP está bloqueada temporalmente. Intenta más tarde.",
				"unblock_in_seconds": remaining
			},
			headers={
				"Retry-After": str(remaining)
			}
		)
	
	return await call_next(request)


# === Per-Endpoint Rate Limit Decorators ===
# NOTE: OPTIONS bypass is handled in middleware, NOT here via exempt_when

def rate_limit_ask() -> Callable:
	"""
	Rate limit for /ask endpoint (EXPENSIVE - OpenAI).
	
	Strict limit to prevent cost explosion.
	OPTIONS bypass handled in middleware.
	"""
	return limiter.limit("20/hour;5/minute")


def rate_limit_notification() -> Callable:
	"""
	Rate limit for /notifications/analyze (VERY EXPENSIVE - Document Intelligence).
	
	Very strict limit due to high computational cost.
	OPTIONS bypass handled in middleware.
	"""
	return limiter.limit("10/hour;2/minute")


def rate_limit_auth() -> Callable:
	"""
	Rate limit for auth endpoints (prevent brute force).
	OPTIONS bypass handled in middleware.
	"""
	return limiter.limit("5/minute")


def rate_limit_admin() -> Callable:
	"""
	Rate limit for admin endpoints.
	OPTIONS bypass handled in middleware.
	"""
	return limiter.limit("20/minute")


def rate_limit_read() -> Callable:
	"""
	Rate limit for read-only endpoints (less strict).
	OPTIONS bypass handled in middleware.
	"""
	return limiter.limit("60/minute")