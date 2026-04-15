export type Tributo = "IRPF" | "IVA" | "ISD" | "ITP" | "PLUSVALIA";

export const TRIBUTO_LABELS: Record<Tributo, string> = {
  IRPF: "IRPF",
  IVA: "IVA",
  ISD: "Sucesiones y Donaciones",
  ITP: "Transmisiones Patrimoniales",
  PLUSVALIA: "Plusvalía Municipal",
};

export type Fase =
  | "COMPROBACION_REQUERIMIENTO"
  | "COMPROBACION_PROPUESTA"
  | "COMPROBACION_POST_ALEGACIONES"
  | "LIQUIDACION_FIRME_PLAZO_RECURSO"
  | "SANCIONADOR_INICIADO"
  | "SANCIONADOR_PROPUESTA"
  | "SANCIONADOR_IMPUESTA"
  | "REPOSICION_INTERPUESTA"
  | "TEAR_INTERPUESTA"
  | "TEAR_AMPLIACION_POSIBLE"
  | "FUERA_DE_ALCANCE"
  | "INDETERMINADA";

export const FASE_LABELS: Record<Fase, string> = {
  COMPROBACION_REQUERIMIENTO: "Requerimiento",
  COMPROBACION_PROPUESTA: "Propuesta de liquidación",
  COMPROBACION_POST_ALEGACIONES: "Alegaciones presentadas",
  LIQUIDACION_FIRME_PLAZO_RECURSO: "Plazo de recurso",
  SANCIONADOR_INICIADO: "Sancionador iniciado",
  SANCIONADOR_PROPUESTA: "Propuesta de sanción",
  SANCIONADOR_IMPUESTA: "Sanción impuesta",
  REPOSICION_INTERPUESTA: "Reposición interpuesta",
  TEAR_INTERPUESTA: "TEAR interpuesta",
  TEAR_AMPLIACION_POSIBLE: "Ampliación TEAR posible",
  FUERA_DE_ALCANCE: "Fuera de alcance",
  INDETERMINADA: "Indeterminada",
};

export type TipoDocumento =
  | "REQUERIMIENTO"
  | "PROPUESTA_LIQUIDACION"
  | "LIQUIDACION_PROVISIONAL"
  | "ACUERDO_INICIO_SANCIONADOR"
  | "PROPUESTA_SANCION"
  | "ACUERDO_IMPOSICION_SANCION"
  | "ESCRITO_ALEGACIONES_USUARIO"
  | "ESCRITO_REPOSICION_USUARIO"
  | "ESCRITO_RECLAMACION_TEAR_USUARIO"
  | "ACTA_INSPECCION"
  | "PROVIDENCIA_APREMIO"
  | "RESOLUCION_TEAR"
  | "RESOLUCION_TEAC"
  | "SENTENCIA_JUDICIAL"
  | "JUSTIFICANTE_PAGO"
  | "FACTURA"
  | "ESCRITURA"
  | "LIBRO_REGISTRO"
  | "OTROS";

export type EstadoExpediente =
  | "borrador"
  | "en_analisis"
  | "dictamen_listo"
  | "archivado";

export interface DocumentoEstructurado {
  id: string;
  nombre_original: string;
  tipo_documento: TipoDocumento;
  fecha_acto: string | null;
  datos: Record<string, unknown>;
  clasificacion_confianza: number;
}

export interface Expediente {
  id: string;
  titulo: string;
  tributo: Tributo;
  ccaa: string;
  estado: EstadoExpediente;
  fase_detectada: Fase;
  fase_confianza: number;
  num_documentos: number;
  dias_restantes: number | null;
  creado_en: string;
  actualizado_en: string;
}

export interface ExpedienteDetalle extends Expediente {
  documentos: DocumentoEstructurado[];
  brief: Brief | null;
  dictamen: Dictamen | null;
  escritos: Escrito[];
}

export interface Brief {
  id: string;
  texto: string;
  chat_history: Array<{ role: "user" | "assistant"; content: string }>;
  creado_en: string;
}

export interface ArgumentoVerificado {
  regla_id: string;
  descripcion: string;
  cita_verificada: string;
  referencia_normativa_canonica: string;
  confianza: number;
  datos_disparo: Record<string, unknown>;
  impacto_estimado: string | null;
}

export interface Dictamen {
  id: string;
  expediente_id: string;
  argumentos: ArgumentoVerificado[];
  resumen: string;
  creado_en: string;
}

export interface Escrito {
  id: string;
  expediente_id: string;
  plantilla: string;
  contenido_markdown: string;
  exportado: boolean;
  creado_en: string;
  actualizado_en: string;
}

export interface CuotaMensual {
  plan: "particular" | "autonomo" | "creator";
  usados: number;
  limite: number;
  restantes: number;
  extras_disponibles: number;
  precio_extra_eur: number;
  reset_en: string;
}
