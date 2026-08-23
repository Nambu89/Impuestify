/**
 * Tokens y rutas para los E2E de Playwright.
 *
 * Por que existe: hasta el 2026-08-23 cuatro specs llevaban el JWT pegado como
 * literal en el fichero. Los que habia estaban caducados, asi que el riesgo era
 * nulo, pero el patron garantizaba que el dia que alguien los regenerase
 * acabarian tokens VIVOS en el repositorio. Aqui se firman al vuelo.
 *
 * Orden de resolucion:
 *   1. `E2E_ACCESS_TOKEN` (+ `E2E_REFRESH_TOKEN` opcional) — token ya emitido.
 *   2. `JWT_SECRET_KEY` del entorno, o del `.env` de la raiz — se firma HS256
 *      con `node:crypto`, sin dependencias nuevas.
 *   3. Si no hay ninguna de las dos, se lanza un error explicando que exportar.
 *
 * El secreto NUNCA se escribe en el fichero ni se vuelca en los logs.
 */

import { createHmac } from 'node:crypto'
import * as fs from 'node:fs'
import * as path from 'node:path'

/** Raiz del repo, derivada de la ubicacion de este fichero. */
export const REPO_ROOT = path.resolve(__dirname, '..', '..', '..')

/** `tests/e2e/screenshots` — se crea si no existe. */
export const SCREENSHOTS_DIR = path.join(__dirname, '..', 'screenshots')

/** `tests/e2e/fixtures`. */
export const FIXTURES_DIR = path.join(__dirname, '..', 'fixtures')

/** Usuario de pruebas por defecto — el mismo que llevaban los tokens literales. */
export const TEST_USER = {
  sub: process.env.E2E_USER_SUB || 'test-particular-00000001',
  email: process.env.E2E_USER_EMAIL || 'test.particular@impuestify.es',
}

export interface TestTokens {
  access: string
  refresh: string
}

function base64url(input: Buffer | string): string {
  return Buffer.from(input)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

/**
 * Lee una clave del `.env` de la raiz. Replica las reglas de `python-dotenv`,
 * que es lo que usa el backend, en lo que nos afecta: prefijo `export`
 * opcional, valor entrecomillado con el `#` literal dentro, y comentario en
 * linea recortado solo cuando el valor va SIN comillas. Si esto se desvia, se
 * firma con otro secreto y el backend contesta 401 sin decir por que.
 */
function readFromRootEnv(key: string): string | undefined {
  const envPath = path.join(REPO_ROOT, '.env')
  if (!fs.existsSync(envPath)) return undefined

  for (const raw of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const line = raw.trim().replace(/^export\s+/, '')
    if (!line || line.startsWith('#')) continue

    const eq = line.indexOf('=')
    if (eq === -1 || line.slice(0, eq).trim() !== key) continue

    const value = line.slice(eq + 1).trim()

    const quoted = value.match(/^(['"])([\s\S]*?)\1/)
    if (quoted) return quoted[2]

    // Sin comillas: el comentario empieza en una almohadilla precedida de
    // espacio. Una almohadilla pegada al valor es parte del secreto.
    return value.split(/\s+#/)[0].trim()
  }
  return undefined
}

function sign(payload: Record<string, unknown>, secret: string): string {
  const header = base64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = base64url(JSON.stringify(payload))
  const signature = base64url(createHmac('sha256', secret).update(`${header}.${body}`).digest())
  return `${header}.${body}.${signature}`
}

/**
 * Devuelve un par access/refresh valido para el backend local.
 *
 * La forma del payload replica `backend/app/auth/jwt_handler.py`
 * (`create_access_token` / `create_refresh_token`): `sub`, `email`, `iat`,
 * `exp`, `type` y —solo en el refresh— `jti`. `get_current_user` no consulta la
 * base de datos, le basta con que la firma cuadre.
 *
 * LIMITE del refresh: `/auth/refresh` valida el `jti` contra
 * `refresh_token_store` (ver `backend/app/routers/auth.py`), y un `jti` acunado
 * aqui no esta registrado, asi que la RENOVACION fallara. El refresh solo sirve
 * para que el frontend arranque con la sesion puesta. Como el access dura una
 * hora y un spec tarda minutos, la renovacion no llega a dispararse. Si algun
 * dia hace falta, pasa un refresh de verdad por `E2E_REFRESH_TOKEN`.
 */
export function issueTestTokens(user: { sub: string; email: string } = TEST_USER): TestTokens {
  const secret = process.env.JWT_SECRET_KEY || readFromRootEnv('JWT_SECRET_KEY')
  const iat = Math.floor(Date.now() / 1000)

  const access =
    process.env.E2E_ACCESS_TOKEN ||
    (secret
      ? sign({ sub: user.sub, email: user.email, iat, exp: iat + 60 * 60, type: 'access' }, secret)
      : '')

  if (!access) {
    throw new Error(
      'No hay credenciales para los E2E. Exporta JWT_SECRET_KEY (la misma que usa el ' +
        'backend local), o pon un token ya emitido en E2E_ACCESS_TOKEN. ' +
        'NO vuelvas a pegar un JWT literal en el fichero de test.'
    )
  }

  // El refresh NUNCA cae de vuelta al access: llevan `type` distinto y
  // `verify_token(..., token_type=refresh)` lo rechazaria. Si no se puede
  // firmar uno propio, se deja vacio y no se escribe en localStorage.
  const refresh =
    process.env.E2E_REFRESH_TOKEN ||
    (secret
      ? sign(
          {
            sub: user.sub,
            email: user.email,
            iat,
            exp: iat + 7 * 24 * 60 * 60,
            type: 'refresh',
            jti: `e2e-${iat}-${Math.random().toString(36).slice(2, 10)}`,
          },
          secret
        )
      : '')

  return { access, refresh }
}

/** Inyecta el par de tokens en `localStorage` del origen ya cargado en `page`. */
export async function injectTokens(
  page: { evaluate: (fn: (t: TestTokens) => void, arg: TestTokens) => Promise<unknown> },
  tokens: TestTokens
): Promise<void> {
  await page.evaluate((t: TestTokens) => {
    localStorage.setItem('access_token', t.access)
    if (t.refresh) localStorage.setItem('refresh_token', t.refresh)
  }, tokens)
}

/**
 * Crea `tests/e2e/screenshots` si hace falta y devuelve la ruta del fichero.
 * Sirve para cualquier artefacto del test, no solo imagenes (ver `.json` de
 * resultados en algunos specs).
 */
export function artifactPath(name: string): string {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true })
  return path.join(SCREENSHOTS_DIR, name)
}

/** Como `artifactPath`, anadiendo la extension `.png` si falta. */
export function screenshotPath(name: string): string {
  return artifactPath(name.endsWith('.png') ? name : `${name}.png`)
}
