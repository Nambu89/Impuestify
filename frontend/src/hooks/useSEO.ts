import { useEffect } from 'react'

export interface SEOConfig {
  title: string
  description: string
  canonical?: string
  keywords?: string
  og?: {
    title?: string
    description?: string
    image?: string
    type?: string
    url?: string
  }
  twitter?: {
    card?: string
    title?: string
    description?: string
    image?: string
  }
  schema?: object | object[]
  noindex?: boolean
}

const BASE_URL = 'https://impuestify.com'
const DEFAULT_OG_IMAGE = '/images/og-impuestify.png'
const SCHEMA_SCRIPT_ATTR = 'data-useseo-schema'

// --- internal helpers ---

function setMeta(name: string, content: string): HTMLMetaElement {
  let el = document.querySelector<HTMLMetaElement>(`meta[name="${CSS.escape(name)}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('name', name)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
  return el
}

function setProperty(property: string, content: string): HTMLMetaElement {
  let el = document.querySelector<HTMLMetaElement>(`meta[property="${CSS.escape(property)}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('property', property)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
  return el
}

function setLink(rel: string, href: string): HTMLLinkElement {
  let el = document.querySelector<HTMLLinkElement>(`link[rel="${CSS.escape(rel)}"]`)
  if (!el) {
    el = document.createElement('link')
    el.setAttribute('rel', rel)
    document.head.appendChild(el)
  }
  el.setAttribute('href', href)
  return el
}

function removeElement(el: Element | null): void {
  el?.parentNode?.removeChild(el)
}

// --- hook ---

export function useSEO(config: SEOConfig): void {
  useEffect(() => {
    const {
      title,
      description,
      canonical,
      keywords,
      og = {},
      twitter = {},
      schema,
      noindex = false,
    } = config

    const prevTitle = document.title
    document.title = title

    const ogTitle = og.title ?? title
    const ogDescription = og.description ?? description
    const ogImage = og.image ?? DEFAULT_OG_IMAGE
    const ogType = og.type ?? 'website'
    const canonicalUrl = canonical ? `${BASE_URL}${canonical}` : undefined
    const ogUrl = og.url ?? canonicalUrl

    const twitterCard = twitter.card ?? 'summary_large_image'
    const twitterTitle = twitter.title ?? ogTitle
    const twitterDescription = twitter.description ?? ogDescription
    const twitterImage = twitter.image ?? ogImage

    // Track elements we create so we can clean up precisely
    const created: Element[] = []

    const meta = (name: string, content: string) => created.push(setMeta(name, content))
    const prop = (property: string, content: string) => created.push(setProperty(property, content))
    const link = (rel: string, href: string) => created.push(setLink(rel, href))

    // Basic meta
    meta('description', description)
    if (keywords) meta('keywords', keywords)
    if (noindex) meta('robots', 'noindex, nofollow')

    // Canonical
    if (canonicalUrl) link('canonical', canonicalUrl)

    // Open Graph
    prop('og:title', ogTitle)
    prop('og:description', ogDescription)
    prop('og:image', ogImage)
    prop('og:type', ogType)
    if (ogUrl) prop('og:url', ogUrl)

    // Twitter Card
    meta('twitter:card', twitterCard)
    meta('twitter:title', twitterTitle)
    meta('twitter:description', twitterDescription)
    meta('twitter:image', twitterImage)

    // JSON-LD schema
    let schemaScript: HTMLScriptElement | null = null
    if (schema) {
      schemaScript = document.createElement('script')
      schemaScript.type = 'application/ld+json'
      schemaScript.setAttribute(SCHEMA_SCRIPT_ATTR, '')
      const schemas = Array.isArray(schema) ? schema : [schema]
      schemaScript.text = schemas.length === 1
        ? JSON.stringify(schemas[0])
        : JSON.stringify(schemas)
      document.head.appendChild(schemaScript)
    }

    return () => {
      document.title = prevTitle
      for (const el of created) removeElement(el)
      if (schemaScript) removeElement(schemaScript)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    config.title,
    config.description,
    config.canonical,
    config.keywords,
    config.noindex,
    config.og?.title,
    config.og?.description,
    config.og?.image,
    config.og?.type,
    config.og?.url,
    config.twitter?.card,
    config.twitter?.title,
    config.twitter?.description,
    config.twitter?.image,
    // schema serialised to avoid object reference churn
    // eslint-disable-next-line react-hooks/exhaustive-deps
    config.schema ? JSON.stringify(config.schema) : undefined,
  ])
}
