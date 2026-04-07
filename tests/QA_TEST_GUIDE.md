# QA Test Guide — Impuestify

## Usuarios de test

| Usuario | Email | Password | Plan | Perfil |
|---------|-------|----------|------|--------|
| Maria Garcia Lopez | test.particular@impuestify.es | Test2026! | particular | Asalariada, Madrid, 35K EUR, 1 hijo |
| Carlos Martinez Ruiz | test.autonomo@impuestify.es | Test2026! | autonomo | Disenador IAE 844, Cataluna, 3.500 EUR/mes |
| Laura Sanchez Torres | test.creator@impuestify.es | Test2026! | creator | Creadora IAE 8690, Andalucia, IRPF 7%, IG+YT+TikTok |

**Re-seedear:** `cd backend && python scripts/seed_test_users.py`

Suscripciones activas hasta 31/12/2026. Turnstile CAPTCHA bloquea login en localhost — usar inyeccion JWT via API (ver test specs).

---

## Facturas de ejemplo

Generar imagenes: `npx tsx tests/e2e/fixtures/invoices/generate-invoice-images.ts`

| Archivo | Tipo | Base | IVA | IRPF | Total |
|---------|------|------|-----|------|-------|
| factura-autonomo-consultor.png | Asesoria fiscal (3 lineas) | 1.725 EUR | 21% | -15% | 1.828,50 EUR |
| factura-creador-contenido.png | Diseno + redes (5 lineas) | 5.310 EUR | 21% | -7% | 6.053,40 EUR |
| factura-farmacia-proveedor.png | Cofares (7 lineas, 3 tipos IVA + RE) | 301,80 EUR | 4/10/21% | — | 346,38 EUR |
| factura-simplificada-ticket.png | Papeleria (ticket, IVA incluido) | 43,88 EUR | 21% incl. | — | 53,10 EUR |
| factura-intracomunitaria.png | Dev web EU (sin IVA, inversion SP) | 12.500 EUR | exento | — | 12.500 EUR |

---

## Flujos a probar

### 1. Login + navegacion basica

1. Ir a http://localhost:3001/
2. Click "Iniciar Sesion" → login con test.autonomo@impuestify.es
3. Verificar: nombre "Carlos Martinez Ruiz" en header
4. Navegar: Chat, Herramientas, Crypto, Calendario, Configuracion

### 2. Clasificador de facturas (requiere plan autonomo o creator)

1. Login con test.autonomo@impuestify.es
2. Ir a /clasificador-facturas
3. Verificar: zona upload visible, lista vacia, filtro anio "2026"
4. Click "Subir factura" → seleccionar factura-autonomo-consultor.png
5. Esperar 30-60s (Gemini OCR)
6. Verificar resultado:
   - Datos extraidos: emisor, receptor, NIF, fecha, lineas, base, IVA, IRPF, total
   - Clasificacion PGC: cuenta + nombre + confianza
   - Botones "Confirmar" / "Corregir"
7. Verificar que la factura aparece en la lista de "Facturas registradas"
8. Repetir con factura-farmacia-proveedor.png (multi-IVA + RE)

### 3. Contabilidad (requiere facturas subidas)

1. Ir a /contabilidad
2. Tab "Libro Diario": verificar asientos con fecha, N.o asiento, cuenta, nombre, debe, haber, concepto
3. Tab "Libro Mayor": verificar cuentas agrupadas con saldo
4. Tab "Balance": verificar totales debe/haber, indicador cuadra/no cuadra
5. Tab "Perd. y Gan.": verificar ingresos, gastos, resultado del ejercicio
6. Click "Exportar" → CSV y/o Excel

### 4. Settings + suscripcion

1. Ir a /settings
2. Tab "Personal": nombre y email visibles
3. Tab "Suscripcion": plan activo, proximo cobro 31/12/2026
4. Tab "Perfil Fiscal": CCAA, situacion laboral, datos fiscales

### 5. Plan particular bloqueado

1. Login con test.particular@impuestify.es
2. Intentar ir a /clasificador-facturas → debe redirigir a /subscribe o mostrar error
3. Verificar que /chat funciona normalmente

### 6. Plan creator tiene acceso

1. Login con test.creator@impuestify.es
2. Ir a /clasificador-facturas → debe cargar
3. Subir factura-creador-contenido.png
4. Verificar OCR + clasificacion

### 7. Guia fiscal adaptativa

1. Login con test.autonomo@impuestify.es
2. Ir a /guia-fiscal
3. Verificar 8 pasos (autonomo): Personal, Trabajo (con actividad economica), Ahorro, Inmuebles, Familia, Deducciones, Resultado
4. Rellenar datos y verificar estimacion IRPF en barra inferior

### 8. Calculadoras publicas (sin login)

1. /calculadora-retenciones — introducir salario, verificar retencion
2. /calculadora-neto — introducir facturacion autonomo, verificar desglose
3. /calculadora-umbrales — verificar clasificacion empresa
4. /modelos-obligatorios — verificar modelos por perfil

---

## Test E2E automatizado (Playwright)

```bash
# Prerequisitos
cd backend && python scripts/seed_test_users.py
npx tsx tests/e2e/fixtures/invoices/generate-invoice-images.ts

# Ejecutar (backend en :8000, frontend en :3001)
npx playwright test tests/e2e/qa-invoices-contabilidad-full.spec.ts --headed
```

17 tests: login 3 usuarios, upload 5 facturas, contabilidad 4 tabs, reclasificacion, export CSV, mobile responsive.

---

## Notas

- **Turnstile CAPTCHA**: no funciona en localhost. Los test specs inyectan JWT via API directamente.
- **Gemini OCR**: requiere GOOGLE_GEMINI_API_KEY configurada. Sin ella, uploads devuelven 503.
- **Timeout upload**: configurado a 120s (Gemini tarda 30-60s).
- **Multi-IVA farmacia**: el modelo actual solo soporta 1 tipo IVA por factura. La factura de farmacia (3 tipos) mostrara advertencia de IVA incorrecto — es una limitacion conocida.
