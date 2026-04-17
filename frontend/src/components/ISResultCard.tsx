import { TrendingDown, TrendingUp, Percent, Minus, Plus, ArrowRight } from 'lucide-react'
import type { ISEstimateResult } from '../types/is'
import './ISResultCard.css'

interface Props {
  result: ISEstimateResult
}

const fmtEur = (n: number): string =>
  n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' EUR'

export default function ISResultCard({ result }: Props) {
  const isDevolver = result.tipo === 'a_devolver'
  const finalClass = isDevolver ? 'is-result__amount--negative' : 'is-result__amount--positive'

  return (
    <div className="is-result">
      <div className="is-result__header">
        <h3>Resultado Modelo 200 — Ejercicio {result.ejercicio}</h3>
        <div className="is-result__regime">
          {result.territorio}
        </div>
        <span className="is-result__regime-badge">
          {result.regimen}
        </span>
      </div>

      <div className="is-result__lines">
        {/* Resultado contable */}
        <div className="is-result__line">
          <span className="is-result__line-label">Resultado contable</span>
          <span className="is-result__line-amount">{fmtEur(result.resultado_contable)}</span>
        </div>

        {/* Ajustes */}
        <div className="is-result__line">
          <span className="is-result__line-label">
            <Plus size={14} /> Ajustes positivos
          </span>
          <span className="is-result__line-amount">{fmtEur(result.ajustes_positivos)}</span>
        </div>
        <div className="is-result__line">
          <span className="is-result__line-label">
            <Minus size={14} /> Ajustes negativos
          </span>
          <span className="is-result__line-amount">-{fmtEur(result.ajustes_negativos)}</span>
        </div>

        {/* Base imponible previa */}
        <div className="is-result__line is-result__line--separator">
          <span className="is-result__line-label">
            <ArrowRight size={14} /> Base imponible previa
          </span>
          <span className="is-result__line-amount">{fmtEur(result.base_imponible_previa)}</span>
        </div>

        {/* BINs */}
        {result.compensacion_bins > 0 && (
          <div className="is-result__line is-result__line--sub">
            <span className="is-result__line-label">
              <Minus size={12} /> Compensaci&oacute;n BINs
            </span>
            <span className="is-result__line-amount">-{fmtEur(result.compensacion_bins)}</span>
          </div>
        )}

        {/* Base imponible */}
        <div className="is-result__line is-result__line--separator">
          <span className="is-result__line-label">Base imponible</span>
          <span className="is-result__line-amount">{fmtEur(result.base_imponible)}</span>
        </div>

        {/* Tipo gravamen */}
        <div className="is-result__line is-result__line--sub">
          <span className="is-result__line-label">
            <Percent size={12} /> Tipo gravamen: {result.tipo_gravamen_aplicado}
          </span>
          <span className="is-result__line-amount" />
        </div>

        {/* Cuota integra */}
        <div className="is-result__line">
          <span className="is-result__line-label">Cuota &iacute;ntegra</span>
          <span className="is-result__line-amount">{fmtEur(result.cuota_integra)}</span>
        </div>

        {/* Deducciones */}
        {result.deducciones_total > 0 && (
          <>
            <div className="is-result__line">
              <span className="is-result__line-label">
                <Minus size={14} /> Deducciones
              </span>
              <span className="is-result__line-amount">-{fmtEur(result.deducciones_total)}</span>
            </div>
            {result.deducciones_detalle.id > 0 && (
              <div className="is-result__line is-result__line--sub">
                <span className="is-result__line-label">I+D</span>
                <span className="is-result__line-amount">{fmtEur(result.deducciones_detalle.id)}</span>
              </div>
            )}
            {result.deducciones_detalle.it > 0 && (
              <div className="is-result__line is-result__line--sub">
                <span className="is-result__line-label">Innovaci&oacute;n tecnol&oacute;gica</span>
                <span className="is-result__line-amount">{fmtEur(result.deducciones_detalle.it)}</span>
              </div>
            )}
            {result.deducciones_detalle.reserva_capitalizacion > 0 && (
              <div className="is-result__line is-result__line--sub">
                <span className="is-result__line-label">Reserva capitalizaci&oacute;n</span>
                <span className="is-result__line-amount">{fmtEur(result.deducciones_detalle.reserva_capitalizacion)}</span>
              </div>
            )}
            {result.deducciones_detalle.donativos > 0 && (
              <div className="is-result__line is-result__line--sub">
                <span className="is-result__line-label">Donativos</span>
                <span className="is-result__line-amount">{fmtEur(result.deducciones_detalle.donativos)}</span>
              </div>
            )}
            {result.deducciones_detalle.empleo_discapacidad > 0 && (
              <div className="is-result__line is-result__line--sub">
                <span className="is-result__line-label">Empleo discapacidad</span>
                <span className="is-result__line-amount">{fmtEur(result.deducciones_detalle.empleo_discapacidad)}</span>
              </div>
            )}
            {result.deducciones_detalle.ric > 0 && (
              <div className="is-result__line is-result__line--sub">
                <span className="is-result__line-label">RIC Canarias</span>
                <span className="is-result__line-amount">{fmtEur(result.deducciones_detalle.ric)}</span>
              </div>
            )}
          </>
        )}

        {/* Bonificaciones */}
        {result.bonificaciones_total > 0 && (
          <div className="is-result__line">
            <span className="is-result__line-label">
              <Minus size={14} /> Bonificaciones
            </span>
            <span className="is-result__line-amount">-{fmtEur(result.bonificaciones_total)}</span>
          </div>
        )}

        {/* Cuota liquida */}
        <div className="is-result__line is-result__line--separator">
          <span className="is-result__line-label">Cuota l&iacute;quida</span>
          <span className="is-result__line-amount">{fmtEur(result.cuota_liquida)}</span>
        </div>

        {/* Retenciones */}
        {result.retenciones > 0 && (
          <div className="is-result__line">
            <span className="is-result__line-label">
              <Minus size={14} /> Retenciones e ingresos a cuenta
            </span>
            <span className="is-result__line-amount">-{fmtEur(result.retenciones)}</span>
          </div>
        )}

        {/* Pagos fraccionados */}
        {result.pagos_fraccionados > 0 && (
          <div className="is-result__line">
            <span className="is-result__line-label">
              <Minus size={14} /> Pagos fraccionados realizados
            </span>
            <span className="is-result__line-amount">-{fmtEur(result.pagos_fraccionados)}</span>
          </div>
        )}

        {/* RESULTADO FINAL */}
        <div className="is-result__line is-result__line--final">
          <span className="is-result__line-label">
            {isDevolver ? <TrendingDown size={18} /> : <TrendingUp size={18} />}
            {isDevolver ? 'A devolver' : 'A ingresar'}
          </span>
          <span className={`is-result__line-amount ${finalClass}`}>
            {fmtEur(Math.abs(result.resultado_liquidacion))}
          </span>
        </div>
      </div>

      {/* Tipo efectivo */}
      <div className="is-result__tipo-efectivo">
        <span className="is-result__tipo-badge">
          <Percent size={14} /> Tipo efectivo: {result.tipo_efectivo.toFixed(2)}%
        </span>
      </div>

      {/* BIN generada */}
      {result.bin_generada > 0 && (
        <div className="is-result__line is-result__line--sub" style={{ paddingTop: '0.5rem' }}>
          <span className="is-result__line-label">BIN generada (compensable en ejercicios futuros)</span>
          <span className="is-result__line-amount">{fmtEur(result.bin_generada)}</span>
        </div>
      )}

      {/* Pagos fraccionados 202 */}
      {(result.pago_fraccionado_202_art40_2 !== null || result.pago_fraccionado_202_art40_3 !== null) && (
        <div className="is-result__pagos202">
          <h4>Estimaci&oacute;n pagos fraccionados Modelo 202</h4>
          {result.pago_fraccionado_202_art40_2 !== null && (
            <div className="is-result__pagos202-item">
              <span className="is-result__pagos202-label">Art. 40.2 (sobre cuota): cada pago</span>
              <span className="is-result__pagos202-amount">{fmtEur(result.pago_fraccionado_202_art40_2)}</span>
            </div>
          )}
          {result.pago_fraccionado_202_art40_3 !== null && (
            <div className="is-result__pagos202-item">
              <span className="is-result__pagos202-label">Art. 40.3 (sobre base): cada pago</span>
              <span className="is-result__pagos202-amount">{fmtEur(result.pago_fraccionado_202_art40_3)}</span>
            </div>
          )}
          <div className="is-result__pagos202-item" style={{ opacity: 0.5, fontSize: '0.78rem' }}>
            <span className="is-result__pagos202-label">Plazos: abril, octubre, diciembre</span>
            <span />
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="is-result__disclaimer">
        {result.disclaimer}
      </div>
    </div>
  )
}
