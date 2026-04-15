import "./PlazoBadge.css";

interface Props {
  dias_restantes: number | null;
}

export function PlazoBadge({ dias_restantes }: Props) {
  if (dias_restantes === null) return null;

  let clase: string;
  let texto: string;

  if (dias_restantes < 0) {
    clase = "plazo-gris";
    texto = "Vencido";
  } else if (dias_restantes < 5) {
    clase = "plazo-rojo";
    texto = dias_restantes === 1 ? "1 día" : `${dias_restantes} días`;
  } else if (dias_restantes <= 15) {
    clase = "plazo-ambar";
    texto = `${dias_restantes} días`;
  } else {
    clase = "plazo-verde";
    texto = `${dias_restantes} días`;
  }

  return (
    <span
      className={`plazo-badge ${clase}`}
      aria-label={`Plazo ${texto}`}
    >
      {texto}
    </span>
  );
}
