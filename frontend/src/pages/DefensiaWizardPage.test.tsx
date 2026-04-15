import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { DefensiaWizardPage } from "./DefensiaWizardPage";

const apiRequestMock = vi.fn();
vi.mock("../hooks/useApi", () => ({
  useApi: () => ({ apiRequest: apiRequestMock }),
}));

const uploadMock = vi.fn();
vi.mock("../hooks/useDefensiaUpload", () => ({
  useDefensiaUpload: () => ({ upload: uploadMock, progress: 0, uploading: false }),
}));

const navigateMock = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("../hooks/useSEO", () => ({ useSEO: () => {} }));

describe("DefensiaWizardPage", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
    uploadMock.mockReset();
    navigateMock.mockReset();
  });

  function renderPage() {
    return render(
      <MemoryRouter>
        <DefensiaWizardPage />
      </MemoryRouter>,
    );
  }

  it("paso 1: muestra TributoSelect y next disabled sin selección", () => {
    renderPage();
    expect(screen.getByText(/paso 1/i)).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
    const siguiente = screen.getByRole("button", { name: /siguiente/i });
    expect(siguiente).toBeDisabled();
  });

  it("paso 1 -> 2: seleccionar tributo habilita siguiente y crea expediente", async () => {
    apiRequestMock.mockResolvedValueOnce({ id: "exp-new-1" });
    const user = userEvent.setup();
    renderPage();
    await user.selectOptions(screen.getByRole("combobox"), "IVA");
    const siguiente = screen.getByRole("button", { name: /siguiente/i });
    expect(siguiente).not.toBeDisabled();
    await user.click(siguiente);
    expect(apiRequestMock).toHaveBeenCalledWith(
      "/api/defensia/expedientes",
      expect.objectContaining({ method: "POST" }),
    );
    expect(await screen.findByText(/paso 2/i)).toBeInTheDocument();
  });

  it("paso 2: sin documentos el botón siguiente está deshabilitado", async () => {
    apiRequestMock.mockResolvedValueOnce({ id: "exp-new-1" });
    const user = userEvent.setup();
    renderPage();
    await user.selectOptions(screen.getByRole("combobox"), "IRPF");
    await user.click(screen.getByRole("button", { name: /siguiente/i }));
    await screen.findByText(/paso 2/i);
    expect(
      screen.getByRole("button", { name: /siguiente/i }),
    ).toBeDisabled();
  });

  it("botón atrás vuelve al paso anterior", async () => {
    apiRequestMock.mockResolvedValueOnce({ id: "exp-new-1" });
    const user = userEvent.setup();
    renderPage();
    await user.selectOptions(screen.getByRole("combobox"), "ISD");
    await user.click(screen.getByRole("button", { name: /siguiente/i }));
    await screen.findByText(/paso 2/i);
    await user.click(screen.getByRole("button", { name: /atrás/i }));
    expect(screen.getByText(/paso 1/i)).toBeInTheDocument();
  });

  it("muestra DisclaimerBanner en todos los pasos", () => {
    renderPage();
    expect(
      screen.getByText(/no sustituye asesoramiento profesional/i),
    ).toBeInTheDocument();
  });

  it("tras upload exitoso con fase_detectada, el paso 3 muestra la fase real", async () => {
    // 1. Create expediente
    apiRequestMock.mockResolvedValueOnce({ id: "exp-new-1" });
    // 2. Upload returns Fase 1 auto-extraction result
    uploadMock.mockResolvedValueOnce({
      id: "doc-1",
      nombre_original: "liquidacion.pdf",
      tipo_documento: "LIQUIDACION_PROVISIONAL",
      clasificacion_confianza: 0.92,
      fecha_acto: "2026-01-15",
      fase_detectada: "LIQUIDACION_FIRME_PLAZO_RECURSO",
      fase_confianza: 0.9,
      created_at: "2026-04-15T00:00:00Z",
    });

    const user = userEvent.setup();
    renderPage();

    // Paso 1 -> 2
    await user.selectOptions(screen.getByRole("combobox"), "IRPF");
    await user.click(screen.getByRole("button", { name: /siguiente/i }));
    await screen.findByText(/paso 2/i);

    // Subir fichero
    const file = new File(["%PDF"], "liquidacion.pdf", {
      type: "application/pdf",
    });
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    expect(input).toBeTruthy();
    await user.upload(input, file);

    // Avanzar paso 2 -> 3
    await user.click(screen.getByRole("button", { name: /siguiente/i }));
    await screen.findByText(/paso 3/i);

    // El paso 3 ahora muestra la FaseBadge con la fase real (NO el
    // placeholder "Analizando los documentos...")
    expect(
      screen.getByLabelText(/plazo de recurso/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/analizando los documentos/i),
    ).not.toBeInTheDocument();
  });
});
