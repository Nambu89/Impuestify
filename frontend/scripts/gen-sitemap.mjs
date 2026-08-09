#!/usr/bin/env node
/**
 * Genera public/sitemap.xml a partir de una lista única de rutas públicas.
 *
 * lastmod se deriva de la fecha del último commit de git del fichero de la página
 * (refleja la frescura real del contenido). Si git no está disponible (p.ej. clon
 * shallow en CI), cae a la fecha de modificación del fichero; si el fichero no existe,
 * usa la fecha de hoy. El script NUNCA sale con error: ante cualquier fallo conserva
 * el sitemap existente, para no romper el build.
 *
 * Uso:  node scripts/gen-sitemap.mjs       (o:  npm run gen:sitemap)
 *
 * Mantén ROUTES como la ÚNICA fuente de verdad del sitemap: al añadir una página
 * pública nueva, añádela aquí (y a public/robots.txt).
 */
import { execSync } from 'node:child_process'
import { existsSync, statSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const BASE_URL = 'https://impuestify.com'
const FRONTEND_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')

// loc → ruta pública | file → fichero de la página (para lastmod) | priority | changefreq
const ROUTES = [
    { loc: '/', file: 'src/pages/Home.tsx', priority: '1.0', changefreq: 'weekly' },
    { loc: '/calculadora-retenciones', file: 'src/pages/CalculadoraRetencionesPage.tsx', priority: '0.9', changefreq: 'weekly' },
    { loc: '/calculadora-neto', file: 'src/pages/NetSalaryPage.tsx', priority: '0.9', changefreq: 'weekly' },
    { loc: '/creadores-de-contenido', file: 'src/pages/CreatorsPage.tsx', priority: '0.9', changefreq: 'weekly' },
    { loc: '/farmacias', file: 'src/pages/FarmaciasPage.tsx', priority: '0.8', changefreq: 'monthly' },
    { loc: '/subscribe', file: 'src/pages/SubscribePage.tsx', priority: '0.8', changefreq: 'monthly' },
    { loc: '/territorios-forales', file: 'src/pages/ForalPage.tsx', priority: '0.7', changefreq: 'monthly' },
    { loc: '/ceuta-melilla', file: 'src/pages/CeutaMelillaPage.tsx', priority: '0.7', changefreq: 'monthly' },
    { loc: '/canarias', file: 'src/pages/CanariasPage.tsx', priority: '0.7', changefreq: 'monthly' },
    { loc: '/calculadora-umbrales', file: 'src/pages/CalculadoraUmbralesPage.tsx', priority: '0.7', changefreq: 'monthly' },
    { loc: '/modelos-obligatorios', file: 'src/pages/ModelObligationsPage.tsx', priority: '0.7', changefreq: 'monthly' },
    { loc: '/modelo-200', file: 'src/pages/Modelo200Page.tsx', priority: '0.7', changefreq: 'monthly' },
    { loc: '/modelo-202', file: 'src/pages/Modelo202Page.tsx', priority: '0.7', changefreq: 'monthly' },
    { loc: '/register', file: 'src/pages/Register.tsx', priority: '0.7', changefreq: 'monthly' },
    { loc: '/checklist-borrador', file: 'src/pages/ChecklistBorradorPage.tsx', priority: '0.6', changefreq: 'monthly' },
    { loc: '/obligado-declarar', file: 'src/pages/ObligadoDeclararPage.tsx', priority: '0.6', changefreq: 'monthly' },
    { loc: '/login', file: 'src/pages/Login.tsx', priority: '0.6', changefreq: 'monthly' },
    { loc: '/sobre-mi', file: 'src/pages/SobreMiPage.tsx', priority: '0.6', changefreq: 'monthly' },
    { loc: '/contact', file: 'src/pages/ContactPage.tsx', priority: '0.5', changefreq: 'monthly' },
    { loc: '/privacy-policy', file: 'src/pages/PrivacyPolicyPage.tsx', priority: '0.4', changefreq: 'monthly' },
    { loc: '/terms', file: 'src/pages/TermsPage.tsx', priority: '0.4', changefreq: 'monthly' },
    { loc: '/politica-cookies', file: 'src/pages/CookiePolicyPage.tsx', priority: '0.3', changefreq: 'monthly' },
    { loc: '/ai-transparency', file: 'src/pages/AITransparencyPage.tsx', priority: '0.3', changefreq: 'monthly' },
    { loc: '/data-retention', file: 'src/pages/DataRetentionPage.tsx', priority: '0.3', changefreq: 'monthly' },
]

function today() {
    return new Date().toISOString().slice(0, 10)
}

function lastmodFor(file) {
    const abs = resolve(FRONTEND_ROOT, file)
    // 1) fecha del último commit de git (frescura real del contenido)
    try {
        const out = execSync(`git log -1 --format=%cs -- "${file}"`, {
            cwd: FRONTEND_ROOT,
            stdio: ['ignore', 'pipe', 'ignore'],
        })
            .toString()
            .trim()
        if (/^\d{4}-\d{2}-\d{2}$/.test(out)) return out
    } catch {
        /* git no disponible o fichero sin historia: seguimos */
    }
    // 2) fecha de modificación del fichero
    try {
        if (existsSync(abs)) return statSync(abs).mtime.toISOString().slice(0, 10)
    } catch {
        /* ignore */
    }
    // 3) hoy
    if (!existsSync(abs)) console.warn(`[gen-sitemap] aviso: no existe ${file}, uso la fecha de hoy`)
    return today()
}

function build() {
    const urls = ROUTES.map((r) => {
        const lastmod = lastmodFor(r.file)
        return `  <url>\n    <loc>${BASE_URL}${r.loc}</loc>\n    <lastmod>${lastmod}</lastmod>\n    <changefreq>${r.changefreq}</changefreq>\n    <priority>${r.priority}</priority>\n  </url>`
    }).join('\n')
    return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`
}

try {
    const xml = build()
    writeFileSync(resolve(FRONTEND_ROOT, 'public/sitemap.xml'), xml, 'utf8')
    console.log(`[gen-sitemap] sitemap.xml generado con ${ROUTES.length} URLs`)
} catch (err) {
    console.warn('[gen-sitemap] no se pudo generar el sitemap, se conserva el existente:', err?.message)
}
// nunca fallar el build
process.exit(0)
