/**
 * Bloque reusable que muestra los datos del titular del servicio en
 * las paginas legales (Terminos, Privacidad, Cookies, Aviso Legal).
 *
 * Cumple LSSI-CE Art. 10 (identificacion del prestador) y RGPD Art. 13
 * (responsable del tratamiento).
 */
import { LEGAL_ENTITY } from "./legalData";

interface Props {
  /** Titulo de la seccion. Por defecto: "Titular del servicio". */
  title?: string;
  /** Si true, muestra el rotulo "Responsable del tratamiento" (RGPD). */
  asDataController?: boolean;
}

export function LegalEntity({ title, asDataController = false }: Props) {
  const sectionTitle =
    title ?? (asDataController ? "Responsable del tratamiento" : "Titular del servicio");

  return (
    <section>
      <h2>{sectionTitle}</h2>
      <p>
        En cumplimiento del art&iacute;culo 10 de la Ley 34/2002, de 11 de julio, de Servicios
        de la Sociedad de la Informaci&oacute;n y de Comercio Electr&oacute;nico (LSSI-CE), y del
        art&iacute;culo 13 del Reglamento (UE) 2016/679 (RGPD), se informa al usuario de los
        siguientes datos identificativos del titular del servicio
        {asDataController ? " y responsable del tratamiento de datos personales" : ""}:
      </p>

      <ul>
        <li>
          <strong>Titular:</strong> {LEGAL_ENTITY.name}
        </li>
        <li>
          <strong>{LEGAL_ENTITY.dniCifLabel}:</strong> {LEGAL_ENTITY.dniCif}
        </li>
        <li>
          <strong>Domicilio:</strong> {LEGAL_ENTITY.address}, {LEGAL_ENTITY.cityProvince} ({LEGAL_ENTITY.pais})
        </li>
        <li>
          <strong>Correo electr&oacute;nico de contacto:</strong>{" "}
          <a href={`mailto:${LEGAL_ENTITY.contactEmail}`}>{LEGAL_ENTITY.contactEmail}</a>
        </li>
        <li>
          <strong>Correo para ejercer derechos de protecci&oacute;n de datos:</strong>{" "}
          <a href={`mailto:${LEGAL_ENTITY.privacyEmail}`}>{LEGAL_ENTITY.privacyEmail}</a>
        </li>
        <li>
          <strong>Sitio web:</strong>{" "}
          <a href={LEGAL_ENTITY.website} target="_blank" rel="noreferrer">
            {LEGAL_ENTITY.website}
          </a>
        </li>
        {LEGAL_ENTITY.registroMercantil && (
          <li>
            <strong>Registro Mercantil:</strong> {LEGAL_ENTITY.registroMercantil}
          </li>
        )}
      </ul>

      <div className="alert alert-info">
        <strong>Nota sobre la forma jur&iacute;dica:</strong>
        <p>{LEGAL_ENTITY.legalFormNote}</p>
      </div>
    </section>
  );
}
