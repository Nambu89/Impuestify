import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TributoSelect } from "./TributoSelect";

describe("TributoSelect", () => {
  it("renderiza las 5 opciones de tributo", () => {
    render(<TributoSelect value={null} onChange={() => {}} />);
    const select = screen.getByLabelText(/tributo/i) as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.value);
    expect(options).toEqual(
      expect.arrayContaining(["IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"]),
    );
  });

  it("dispara onChange con el Tributo seleccionado", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<TributoSelect value={null} onChange={onChange} />);
    await user.selectOptions(screen.getByLabelText(/tributo/i), "IVA");
    expect(onChange).toHaveBeenCalledWith("IVA");
  });

  it("expone un aria-label descriptivo", () => {
    render(<TributoSelect value="IRPF" onChange={() => {}} />);
    expect(screen.getByLabelText(/tributo/i)).toBeInTheDocument();
  });
});
