/**
 * Datos legales del titular del servicio.
 *
 * Centralizado aquí para que, cuando se constituya la SL que operará
 * Impuestify, solo haya que actualizar este archivo — las paginas
 * legales (Terminos, Privacidad, Cookies) lo importan.
 *
 * IMPORTANTE: Los valores marcados con `PENDIENTE_` deben ser
 * sustituidos por Fernando Prada antes de publicar en produccion.
 */

export interface LegalEntityData {
  /** Razon social o nombre completo de la persona fisica */
  name: string;
  /** DNI (persona fisica) o CIF (persona juridica) — incluir letra */
  dniCif: string;
  /** Tipo de identificador mostrado: "DNI" o "CIF" */
  dniCifLabel: "DNI" | "CIF";
  /** Domicilio fiscal / social completo */
  address: string;
  /** Codigo postal + ciudad + provincia */
  cityProvince: string;
  pais: string;
  /** Correo de contacto legal/general */
  contactEmail: string;
  /** Correo para ejercer derechos RGPD */
  privacyEmail: string;
  /** Dominio publico */
  website: string;
  /** Nota explicativa sobre forma juridica actual */
  legalFormNote: string;
  /** Inscripcion Registro Mercantil (solo si es SL/SA) */
  registroMercantil?: string;
}

export const LEGAL_ENTITY: LegalEntityData = {
  name: "Fernando Prada Gorge",
  dniCif: "45308568V",
  dniCifLabel: "DNI",
  address: "Calle del Monasterio de Rueda, 1",
  cityProvince: "50007 Zaragoza (Zaragoza)",
  pais: "Espana",
  contactEmail: "fernando.prada@proton.me",
  privacyEmail: "privacy@impuestify.com",
  website: "https://impuestify.com",
  legalFormNote:
    "Impuestify es operado actualmente por Fernando Prada Gorge como persona fisica. " +
    "La constitucion de la sociedad limitada que asumira la titularidad del servicio se " +
    "encuentra en proceso. Este aviso se actualizara con los datos mercantiles (CIF, " +
    "domicilio social y datos de inscripcion en el Registro Mercantil) en el momento " +
    "en que la SL quede constituida.",
};
