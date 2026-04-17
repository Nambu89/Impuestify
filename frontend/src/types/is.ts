/** Modelo 200 — Impuesto sobre Sociedades types */

export type TipoEntidad = "sl" | "slp" | "sa" | "nueva_creacion";

export interface ISEstimateInput {
  workspace_id?: string;
  ejercicio: number;
  tipo_entidad: TipoEntidad;
  territorio: string;
  facturacion_anual: number;
  ejercicios_con_bi_positiva: number;
  ingresos_explotacion?: number;
  gastos_explotacion?: number;
  resultado_contable?: number;
  amortizacion_contable: number;
  amortizacion_fiscal?: number;
  gastos_no_deducibles: number;
  ajustes_negativos: number;
  bins_pendientes: number;
  gasto_id: number;
  gasto_it: number;
  incremento_ffpp: number;
  donativos: number;
  empleados_discapacidad_33: number;
  empleados_discapacidad_65: number;
  dotacion_ric: number;
  es_zec: boolean;
  rentas_ceuta_melilla: number;
  retenciones_ingresos_cuenta: number;
  pagos_fraccionados_realizados: number;
}

export interface ISDeduccionDetalle {
  id: number;
  it: number;
  reserva_capitalizacion: number;
  donativos: number;
  empleo_discapacidad: number;
  ric: number;
}

export interface ISEstimateResult {
  resultado_contable: number;
  ajustes_positivos: number;
  ajustes_negativos: number;
  base_imponible_previa: number;
  compensacion_bins: number;
  base_imponible: number;
  tipo_gravamen_aplicado: string;
  cuota_integra: number;
  deducciones_total: number;
  deducciones_detalle: ISDeduccionDetalle;
  bonificaciones_total: number;
  cuota_liquida: number;
  retenciones: number;
  pagos_fraccionados: number;
  resultado_liquidacion: number;
  tipo: "a_ingresar" | "a_devolver";
  tipo_efectivo: number;
  pago_fraccionado_202_art40_2: number | null;
  pago_fraccionado_202_art40_3: number | null;
  territorio: string;
  regimen: string;
  ejercicio: number;
  prefilled_from_workspace: boolean;
  bin_generada: number;
  disclaimer: string;
}

export interface ISPrefillData {
  workspace_name: string;
  ejercicio: number;
  ingresos_explotacion: number;
  gastos_explotacion: number;
  resultado_contable: number;
  amortizacion_contable: number;
  num_facturas: number;
  periodo_cubierto: string;
  cuentas_desglose: Array<{
    cuenta: string;
    nombre: string;
    importe: number;
  }>;
}
