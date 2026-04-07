/**
 * Generate sample invoice images for E2E testing.
 *
 * Run with: npx tsx tests/e2e/fixtures/invoices/generate-invoice-images.ts
 *
 * Creates 5 invoice PNG files from HTML templates using Playwright:
 *   1. factura-autonomo-consultor.png — Autónomo consultor (IVA 21% + IRPF 15%)
 *   2. factura-creador-contenido.png — Creador de contenido (IVA 21% + IRPF 7% nuevo)
 *   3. factura-farmacia-proveedor.png — Proveedor farmacia (IVA 4%+10%+21% + RE)
 *   4. factura-simplificada-ticket.png — Ticket/factura simplificada
 *   5. factura-intracomunitaria.png — EU service sin IVA (inversión sujeto pasivo)
 */
import { chromium } from 'playwright';
import path from 'path';

const OUTPUT_DIR = path.resolve(__dirname);

// ─── Invoice HTML Templates ───────────────────────────────────

const INVOICE_AUTONOMO_CONSULTOR = `
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 30px; background: #fff; color: #333; width: 700px; }
  .header { display: flex; justify-content: space-between; border-bottom: 3px solid #1e40af; padding-bottom: 15px; margin-bottom: 20px; }
  .title { font-size: 24px; font-weight: bold; color: #1e40af; }
  .info-block { margin-bottom: 15px; }
  .info-block h3 { margin: 0 0 5px; font-size: 13px; color: #666; text-transform: uppercase; }
  .info-block p { margin: 2px 0; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; }
  th { background: #f1f5f9; padding: 8px 12px; text-align: left; font-size: 12px; border-bottom: 2px solid #e2e8f0; }
  td { padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #e2e8f0; }
  .right { text-align: right; }
  .totals { margin-top: 15px; }
  .totals table { width: 350px; margin-left: auto; }
  .totals td { border: none; padding: 4px 12px; }
  .totals .total-row { font-weight: bold; font-size: 16px; border-top: 2px solid #1e40af; }
  .footer { margin-top: 20px; font-size: 11px; color: #666; border-top: 1px solid #e2e8f0; padding-top: 10px; }
</style></head><body>
  <div class="header">
    <div><div class="title">FACTURA</div><div style="font-size:13px;color:#666;">N.º 2026/012</div></div>
    <div style="text-align:right;"><div style="font-size:13px;">Fecha: 31/03/2026</div><div style="font-size:12px;color:#666;">Fecha operación: Marzo 2026</div></div>
  </div>
  <div style="display:flex;gap:40px;">
    <div class="info-block" style="flex:1;">
      <h3>Emisor</h3>
      <p><strong>María García Fernández</strong></p>
      <p>NIF: 23456789D</p>
      <p>Asesora Fiscal y Contable</p>
      <p>IAE: 841 — Servicios jurídicos</p>
      <p>C/ Serrano 112, 3.ºB, 28006 Madrid</p>
    </div>
    <div class="info-block" style="flex:1;">
      <h3>Receptor</h3>
      <p><strong>Inversiones Castellana SL</strong></p>
      <p>CIF: B87654321</p>
      <p>Paseo de la Castellana 50</p>
      <p>28046 Madrid</p>
    </div>
  </div>
  <table>
    <thead><tr><th>Concepto</th><th class="right">Horas</th><th class="right">Precio/h</th><th class="right">Base</th></tr></thead>
    <tbody>
      <tr><td>Asesoría fiscal mensual marzo 2026</td><td class="right">20</td><td class="right">60,00 €</td><td class="right">1.200,00 €</td></tr>
      <tr><td>Preparación declaración IVA T1 2026</td><td class="right">5</td><td class="right">75,00 €</td><td class="right">375,00 €</td></tr>
      <tr><td>Consultas telefónicas y email</td><td class="right">3</td><td class="right">50,00 €</td><td class="right">150,00 €</td></tr>
    </tbody>
  </table>
  <div class="totals"><table>
    <tr><td>Base imponible</td><td class="right">1.725,00 €</td></tr>
    <tr><td>IVA 21%</td><td class="right">362,25 €</td></tr>
    <tr><td>Retención IRPF -15%</td><td class="right">-258,75 €</td></tr>
    <tr class="total-row"><td>TOTAL</td><td class="right">1.828,50 €</td></tr>
  </table></div>
  <div class="footer">
    <p>Forma de pago: Transferencia bancaria | IBAN: ES12 1234 5678 9012 3456 78 | Vencimiento: 15/04/2026</p>
  </div>
</body></html>`;

const INVOICE_CREADOR_CONTENIDO = `
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 30px; background: #fff; color: #333; width: 700px; }
  .header { display: flex; justify-content: space-between; border-bottom: 3px solid #7c3aed; padding-bottom: 15px; margin-bottom: 20px; }
  .title { font-size: 24px; font-weight: bold; color: #7c3aed; }
  .info-block { margin-bottom: 15px; }
  .info-block h3 { margin: 0 0 5px; font-size: 13px; color: #666; text-transform: uppercase; }
  .info-block p { margin: 2px 0; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; }
  th { background: #f5f3ff; padding: 8px 12px; text-align: left; font-size: 12px; border-bottom: 2px solid #e9e5ff; }
  td { padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #e9e5ff; }
  .right { text-align: right; }
  .totals { margin-top: 15px; }
  .totals table { width: 350px; margin-left: auto; }
  .totals td { border: none; padding: 4px 12px; }
  .totals .total-row { font-weight: bold; font-size: 16px; border-top: 2px solid #7c3aed; }
  .footer { margin-top: 20px; font-size: 11px; color: #666; border-top: 1px solid #e2e8f0; padding-top: 10px; }
  .badge { display: inline-block; background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
</style></head><body>
  <div class="header">
    <div><div class="title">FACTURA</div><div style="font-size:13px;color:#666;">N.º PMR-2026-015</div></div>
    <div style="text-align:right;"><div style="font-size:13px;">Fecha: 28/02/2026</div><div class="badge">IRPF 7% — nuevo autónomo</div></div>
  </div>
  <div style="display:flex;gap:40px;">
    <div class="info-block" style="flex:1;">
      <h3>Emisor</h3>
      <p><strong>Pablo Martínez Ruiz</strong></p>
      <p>NIF: 34567890K</p>
      <p>Diseñador gráfico y creador de contenido</p>
      <p>IAE: 8443 — Diseñadores gráficos</p>
      <p>C/ Valencia 234, 2.º, 08007 Barcelona</p>
    </div>
    <div class="info-block" style="flex:1;">
      <h3>Receptor</h3>
      <p><strong>FoodTech Spain SL</strong></p>
      <p>CIF: B91234567</p>
      <p>C/ Alcalá 100, 28009 Madrid</p>
    </div>
  </div>
  <table>
    <thead><tr><th>Concepto</th><th class="right">Uds.</th><th class="right">Precio</th><th class="right">Base</th></tr></thead>
    <tbody>
      <tr><td>Diseño identidad visual marca "NutriApp"</td><td class="right">1</td><td class="right">2.500,00 €</td><td class="right">2.500,00 €</td></tr>
      <tr><td>Pack 12 posts Instagram + stories (campaña feb.)</td><td class="right">1</td><td class="right">960,00 €</td><td class="right">960,00 €</td></tr>
      <tr><td>Edición vídeo promocional 60s (YouTube + TikTok)</td><td class="right">2</td><td class="right">450,00 €</td><td class="right">900,00 €</td></tr>
      <tr><td>Sesión fotografía producto (20 fotos editadas)</td><td class="right">1</td><td class="right">350,00 €</td><td class="right">350,00 €</td></tr>
      <tr><td>Gestión redes sociales febrero 2026</td><td class="right">1</td><td class="right">600,00 €</td><td class="right">600,00 €</td></tr>
    </tbody>
  </table>
  <div class="totals"><table>
    <tr><td>Base imponible</td><td class="right">5.310,00 €</td></tr>
    <tr><td>IVA 21%</td><td class="right">1.115,10 €</td></tr>
    <tr><td>Retención IRPF -7%</td><td class="right">-371,70 €</td></tr>
    <tr class="total-row"><td>TOTAL</td><td class="right">6.053,40 €</td></tr>
  </table></div>
  <div class="footer">
    <p>Forma de pago: Transferencia bancaria | IBAN: ES98 0049 1234 5678 9012 34 | Vencimiento: 30 días fecha factura</p>
  </div>
</body></html>`;

const INVOICE_FARMACIA_PROVEEDOR = `
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 30px; background: #fff; color: #333; width: 700px; }
  .header { display: flex; justify-content: space-between; border-bottom: 3px solid #059669; padding-bottom: 15px; margin-bottom: 20px; }
  .title { font-size: 24px; font-weight: bold; color: #059669; }
  .info-block { margin-bottom: 15px; }
  .info-block h3 { margin: 0 0 5px; font-size: 13px; color: #666; text-transform: uppercase; }
  .info-block p { margin: 2px 0; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; }
  th { background: #ecfdf5; padding: 8px 10px; text-align: left; font-size: 11px; border-bottom: 2px solid #d1fae5; }
  td { padding: 6px 10px; font-size: 12px; border-bottom: 1px solid #d1fae5; }
  .right { text-align: right; }
  .desglose { margin-top: 15px; background: #f0fdf4; padding: 12px; border-radius: 6px; }
  .desglose table { margin: 5px 0; }
  .desglose th { background: transparent; font-size: 11px; padding: 3px 8px; }
  .desglose td { border: none; padding: 3px 8px; font-size: 12px; }
  .total-box { text-align: right; margin-top: 15px; font-size: 20px; font-weight: bold; color: #059669; }
  .footer { margin-top: 20px; font-size: 11px; color: #666; border-top: 1px solid #e2e8f0; padding-top: 10px; }
</style></head><body>
  <div class="header">
    <div><div class="title">FACTURA</div><div style="font-size:13px;color:#666;">N.º FR-2026-0847</div></div>
    <div style="text-align:right;"><div style="font-size:13px;">Fecha: 15/03/2026</div></div>
  </div>
  <div style="display:flex;gap:40px;">
    <div class="info-block" style="flex:1;">
      <h3>Emisor (Distribuidora)</h3>
      <p><strong>Cofares S.A.U.</strong></p>
      <p>CIF: A28091367</p>
      <p>Ctra. de la Coruña km 13,5</p>
      <p>28023 Madrid</p>
    </div>
    <div class="info-block" style="flex:1;">
      <h3>Receptor (Farmacia)</h3>
      <p><strong>Farmacia González López</strong></p>
      <p>NIF: 43567890L</p>
      <p>C/ Gran Vía 45, 28013 Madrid</p>
    </div>
  </div>
  <table>
    <thead><tr><th>Concepto</th><th class="right">Uds.</th><th class="right">P. Unit.</th><th class="right">Base</th><th class="right">IVA</th><th class="right">RE</th></tr></thead>
    <tbody>
      <tr><td>Ibuprofeno 600mg 40 comp</td><td class="right">10</td><td class="right">3,25 €</td><td class="right">32,50 €</td><td class="right">4%</td><td class="right">0,5%</td></tr>
      <tr><td>Paracetamol 1g 20 comp</td><td class="right">15</td><td class="right">1,80 €</td><td class="right">27,00 €</td><td class="right">4%</td><td class="right">0,5%</td></tr>
      <tr><td>Omeprazol 20mg 28 caps</td><td class="right">8</td><td class="right">4,50 €</td><td class="right">36,00 €</td><td class="right">4%</td><td class="right">0,5%</td></tr>
      <tr><td>Apósito estéril 10x10cm (caja 50)</td><td class="right">3</td><td class="right">12,00 €</td><td class="right">36,00 €</td><td class="right">10%</td><td class="right">1,4%</td></tr>
      <tr><td>Tensiómetro digital brazo</td><td class="right">2</td><td class="right">28,50 €</td><td class="right">57,00 €</td><td class="right">10%</td><td class="right">1,4%</td></tr>
      <tr><td>Crema hidratante corporal 400ml</td><td class="right">6</td><td class="right">8,95 €</td><td class="right">53,70 €</td><td class="right">21%</td><td class="right">5,2%</td></tr>
      <tr><td>Protector solar SPF50 200ml</td><td class="right">4</td><td class="right">14,90 €</td><td class="right">59,60 €</td><td class="right">21%</td><td class="right">5,2%</td></tr>
    </tbody>
  </table>
  <div class="desglose">
    <strong>Desglose IVA + Recargo de Equivalencia</strong>
    <table>
      <thead><tr><th>Tipo</th><th class="right">Base</th><th class="right">Cuota IVA</th><th class="right">RE</th><th class="right">Cuota RE</th></tr></thead>
      <tbody>
        <tr><td>IVA 4%</td><td class="right">95,50 €</td><td class="right">3,82 €</td><td class="right">0,5%</td><td class="right">0,48 €</td></tr>
        <tr><td>IVA 10%</td><td class="right">93,00 €</td><td class="right">9,30 €</td><td class="right">1,4%</td><td class="right">1,30 €</td></tr>
        <tr><td>IVA 21%</td><td class="right">113,30 €</td><td class="right">23,79 €</td><td class="right">5,2%</td><td class="right">5,89 €</td></tr>
      </tbody>
    </table>
  </div>
  <div style="display:flex;justify-content:flex-end;gap:30px;margin-top:15px;">
    <div style="text-align:right;font-size:13px;">
      <div>Total base: 301,80 €</div>
      <div>Total IVA: 36,91 €</div>
      <div>Total RE: 7,67 €</div>
    </div>
    <div class="total-box">TOTAL: 346,38 €</div>
  </div>
  <div class="footer">
    <p>Régimen de Recargo de Equivalencia (Art. 154-163 LIVA) | Forma de pago: Domiciliación bancaria | Vto: 30/03/2026</p>
  </div>
</body></html>`;

const INVOICE_SIMPLIFICADA_TICKET = `
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body { font-family: 'Courier New', monospace; margin: 0; padding: 20px; background: #fff; color: #333; width: 320px; }
  .header { text-align: center; border-bottom: 2px dashed #333; padding-bottom: 10px; margin-bottom: 10px; }
  .header h2 { margin: 0; font-size: 16px; }
  .header p { margin: 2px 0; font-size: 12px; }
  .items { margin: 10px 0; }
  .item { display: flex; justify-content: space-between; font-size: 13px; padding: 2px 0; }
  .separator { border-top: 1px dashed #333; margin: 8px 0; }
  .total { display: flex; justify-content: space-between; font-size: 16px; font-weight: bold; padding: 5px 0; }
  .iva-note { font-size: 11px; color: #666; text-align: center; margin-top: 10px; }
  .footer { text-align: center; font-size: 11px; color: #666; margin-top: 15px; border-top: 2px dashed #333; padding-top: 10px; }
</style></head><body>
  <div class="header">
    <h2>PAPELERÍA LÓPEZ S.L.</h2>
    <p>NIF: B78901234</p>
    <p>C/ Fuencarral 89, 28004 Madrid</p>
    <p style="margin-top:8px;font-weight:bold;">FACTURA SIMPLIFICADA</p>
    <p>N.º: FS-2026-003847</p>
    <p>Fecha: 07/04/2026 — 11:34</p>
  </div>
  <div class="items">
    <div class="item"><span>Pack folios A4 500h</span><span>4,95 €</span></div>
    <div class="item"><span>Tóner HP 305A negro</span><span>34,90 €</span></div>
    <div class="item"><span>Carpeta clasificadora</span><span>7,50 €</span></div>
    <div class="item"><span>Bolígrafos BIC x10</span><span>3,60 €</span></div>
    <div class="item"><span>Cinta adhesiva 3M</span><span>2,15 €</span></div>
  </div>
  <div class="separator"></div>
  <div class="item"><span>Subtotal</span><span>53,10 €</span></div>
  <div class="item"><span>IVA 21% incluido</span><span>9,22 €</span></div>
  <div class="separator"></div>
  <div class="total"><span>TOTAL</span><span>53,10 €</span></div>
  <div class="iva-note">IVA incluido en precios</div>
  <div class="footer">
    <p>Gracias por su compra</p>
  </div>
</body></html>`;

const INVOICE_INTRACOMUNITARIA = `
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 30px; background: #fff; color: #333; width: 700px; }
  .header { display: flex; justify-content: space-between; border-bottom: 3px solid #0369a1; padding-bottom: 15px; margin-bottom: 20px; }
  .title { font-size: 24px; font-weight: bold; color: #0369a1; }
  .info-block { margin-bottom: 15px; }
  .info-block h3 { margin: 0 0 5px; font-size: 13px; color: #666; text-transform: uppercase; }
  .info-block p { margin: 2px 0; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; }
  th { background: #f0f9ff; padding: 8px 12px; text-align: left; font-size: 12px; border-bottom: 2px solid #bae6fd; }
  td { padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #e0f2fe; }
  .right { text-align: right; }
  .eu-notice { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 12px; margin: 15px 0; font-size: 12px; }
  .eu-notice strong { color: #1e40af; }
  .totals { margin-top: 15px; }
  .totals table { width: 350px; margin-left: auto; }
  .totals td { border: none; padding: 4px 12px; }
  .totals .total-row { font-weight: bold; font-size: 16px; border-top: 2px solid #0369a1; }
  .footer { margin-top: 20px; font-size: 11px; color: #666; border-top: 1px solid #e2e8f0; padding-top: 10px; }
</style></head><body>
  <div class="header">
    <div><div class="title">INVOICE / FACTURA</div><div style="font-size:13px;color:#666;">N.º DSM-2026-INT-003</div></div>
    <div style="text-align:right;"><div style="font-size:13px;">Date / Fecha: 15/03/2026</div></div>
  </div>
  <div style="display:flex;gap:40px;">
    <div class="info-block" style="flex:1;">
      <h3>Emisor / Supplier</h3>
      <p><strong>Digital Solutions Madrid S.L.</strong></p>
      <p>CIF: B12345678</p>
      <p>NIF-IVA: ESB12345678</p>
      <p>C/ Velázquez 30, 28001 Madrid, España</p>
    </div>
    <div class="info-block" style="flex:1;">
      <h3>Receptor / Customer</h3>
      <p><strong>TechCorp GmbH</strong></p>
      <p>USt-IdNr: DE123456789</p>
      <p>Friedrichstraße 100</p>
      <p>10117 Berlin, Germany</p>
    </div>
  </div>
  <table>
    <thead><tr><th>Concepto / Description</th><th class="right">Uds.</th><th class="right">Precio</th><th class="right">Base</th></tr></thead>
    <tbody>
      <tr><td>Desarrollo aplicación web (sprint 3, feb 2026)</td><td class="right">1</td><td class="right">8.000,00 €</td><td class="right">8.000,00 €</td></tr>
      <tr><td>Consultoría UX/UI (40 horas)</td><td class="right">40</td><td class="right">100,00 €</td><td class="right">4.000,00 €</td></tr>
      <tr><td>Hosting y mantenimiento mensual</td><td class="right">1</td><td class="right">500,00 €</td><td class="right">500,00 €</td></tr>
    </tbody>
  </table>
  <div class="eu-notice">
    <strong>Inversión del sujeto pasivo</strong> — Exento de IVA conforme al Art. 196 Directiva 2006/112/CE.<br/>
    Prestación de servicios intracomunitarios. Operación declarada en Modelo 349.
  </div>
  <div class="totals"><table>
    <tr><td>Base imponible</td><td class="right">12.500,00 €</td></tr>
    <tr><td>IVA</td><td class="right">Exento</td></tr>
    <tr class="total-row"><td>TOTAL</td><td class="right">12.500,00 €</td></tr>
  </table></div>
  <div class="footer">
    <p>Forma de pago: Transferencia SEPA | IBAN: ES66 2100 1234 5678 9012 34 | BIC: CAIXESBBXXX | Plazo: 30 días</p>
  </div>
</body></html>`;

// ─── Main Generator ──────────────────────────────────────

const INVOICES = [
  { name: 'factura-autonomo-consultor', html: INVOICE_AUTONOMO_CONSULTOR, width: 760, height: 600 },
  { name: 'factura-creador-contenido', html: INVOICE_CREADOR_CONTENIDO, width: 760, height: 700 },
  { name: 'factura-farmacia-proveedor', html: INVOICE_FARMACIA_PROVEEDOR, width: 760, height: 850 },
  { name: 'factura-simplificada-ticket', html: INVOICE_SIMPLIFICADA_TICKET, width: 360, height: 500 },
  { name: 'factura-intracomunitaria', html: INVOICE_INTRACOMUNITARIA, width: 760, height: 650 },
];

async function main() {
  const browser = await chromium.launch({ headless: true });

  for (const inv of INVOICES) {
    const page = await browser.newPage({ viewport: { width: inv.width, height: inv.height } });
    await page.setContent(inv.html, { waitUntil: 'networkidle' });

    const outputPath = path.join(OUTPUT_DIR, `${inv.name}.png`);
    await page.screenshot({ path: outputPath, fullPage: true });
    console.log(`[OK] ${inv.name}.png (${inv.width}x${inv.height})`);
    await page.close();
  }

  await browser.close();
  console.log(`\nDone! ${INVOICES.length} invoice images generated in ${OUTPUT_DIR}`);
}

main().catch(console.error);
