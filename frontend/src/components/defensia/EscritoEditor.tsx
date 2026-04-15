import { useCallback, useEffect, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Save, Loader2 } from "lucide-react";
import "./EscritoEditor.css";

const API_URL = import.meta.env.VITE_API_URL || "/api";

interface Props {
  expedienteId: string;
  escritoId: string;
  contenidoInicial: string;
  readOnly?: boolean;
  onChange?: (contenido: string) => void;
  onSaved: (contenido: string) => void;
}

export function EscritoEditor({
  expedienteId,
  escritoId,
  contenidoInicial,
  readOnly = false,
  onChange,
  onSaved,
}: Props) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const editor = useEditor({
    extensions: [StarterKit],
    content: contenidoInicial,
    editable: !readOnly,
    onUpdate: ({ editor }) => {
      onChange?.(editor.getHTML());
    },
  });

  useEffect(() => {
    if (editor && contenidoInicial !== editor.getHTML()) {
      editor.commands.setContent(contenidoInicial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contenidoInicial]);

  const handleSave = useCallback(async () => {
    if (!editor) return;
    setSaving(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const contenido = editor.getHTML();
      const res = await fetch(
        `${API_URL}/api/defensia/expedientes/${expedienteId}/escrito/${escritoId}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ contenido_markdown: contenido }),
        },
      );
      if (!res.ok) {
        let detail = `Error HTTP ${res.status}`;
        try {
          const data = await res.json();
          detail = data.detail || detail;
        } catch {
          // ignore
        }
        setError(detail);
        return;
      }
      onSaved(contenido);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }, [editor, expedienteId, escritoId, onSaved]);

  return (
    <div className="escrito-editor">
      <EditorContent editor={editor} className="escrito-editor-content" />
      <div className="escrito-editor-footer">
        {error && <span className="escrito-editor-error">{error}</span>}
        {!readOnly && (
          <button
            type="button"
            className="escrito-editor-save"
            onClick={() => void handleSave()}
            disabled={saving}
          >
            {saving ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
            {saving ? "Guardando…" : "Guardar"}
          </button>
        )}
      </div>
    </div>
  );
}
