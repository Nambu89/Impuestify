// Impuestify Service Worker
// Strategy: Network-first for API, Cache-first for static assets

const CACHE_NAME = 'impuestify-v1'
const STATIC_CACHE = 'impuestify-static-v1'

// Assets to precache
const PRECACHE_URLS = [
  '/',
  '/offline.html',
  '/favicon.svg',
  '/icon-192.png',
]

// Routes to cache at runtime
const APP_ROUTES = ['/', '/chat', '/settings', '/workspaces', '/subscribe', '/contact']

// Never cache these paths
const NO_CACHE_PATHS = ['/api/', '/auth/', '/health']

// Install: precache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...')
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  )
})

// Activate: clean old caches, take control immediately
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...')
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key !== STATIC_CACHE)
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  )
})

// Fetch handler
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET requests
  if (request.method !== 'GET') return

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) return

  // Skip API/auth calls — always go to network
  if (NO_CACHE_PATHS.some((path) => url.pathname.startsWith(path))) return

  // Static assets (JS, CSS, images, fonts): Cache-first
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request))
    return
  }

  // App routes: Network-first with offline fallback
  event.respondWith(networkFirst(request))
})

function isStaticAsset(pathname) {
  return /\.(js|css|png|jpg|jpeg|svg|gif|woff2?|ttf|eot|ico)$/.test(pathname) ||
         pathname.startsWith('/assets/')
}

// Cache-first: serve from cache, fall back to network
async function cacheFirst(request) {
  const cached = await caches.match(request)
  if (cached) return cached

  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    return new Response('Offline', { status: 503 })
  }
}

// Network-first: try network, fall back to cache, then offline page
async function networkFirst(request) {
  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    const cached = await caches.match(request)
    if (cached) return cached

    // Offline fallback for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html')
    }

    return new Response('Offline', { status: 503 })
  }
}
