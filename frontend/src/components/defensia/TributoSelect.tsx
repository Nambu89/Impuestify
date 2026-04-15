import type { Tributo } from "../../types/defensia";
import { TRIBUTO_LABELS } from "../../types/defensia";
import "./TributoSelect.css";

interface Props {
  value: Tributo | null;
  onChange: (tributo: Tributo) => void;
  disabled?: boolean;
}

const TRIBUTOS: Tributo[] = ["IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"];

export function TributoSelect({ value, onChange, disabled }: Props) {
  return (
    <label className="tributo-select-wrap">
      <span className="tributo-select-label">Tributo</span>
      <select
        className="tributo-select"
        aria-label="Tributo"
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as Tributo)}
      >
        <option value="" disabled>
          Selecciona un tributo
        </option>
        {TRIBUTOS.map((t) => (
          <option key={t} value={t}>
            {TRIBUTO_LABELS[t]}
          </option>
        ))}
      </select>
    </label>
  );
}
