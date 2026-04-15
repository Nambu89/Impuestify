import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { useDefensiaChat } from "../../hooks/useDefensiaChat";
import { DisclaimerBanner } from "./DisclaimerBanner";
import "./DefensiaChat.css";

interface Props {
  expedienteId: string;
}

export function DefensiaChat({ expedienteId }: Props) {
  const { messages, streaming, error, send } = useDefensiaChat(expedienteId);
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleEnviar = async () => {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;
    setText("");
    await send(trimmed);
  };

  return (
    <div className="defensia-chat">
      <DisclaimerBanner />

      <div className="defensia-chat-messages" role="log">
        {messages.length === 0 && (
          <p className="defensia-chat-empty">
            Pregunta a DefensIA sobre tu expediente. Solo hablará del caso cargado.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`defensia-chat-msg defensia-chat-msg--${m.role}`}>
            <div className="defensia-chat-bubble">{m.content || (m.role === "assistant" && streaming ? "…" : "")}</div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {error && (
        <div className="defensia-chat-error">{error}</div>
      )}

      <form
        className="defensia-chat-input-row"
        onSubmit={(e) => {
          e.preventDefault();
          void handleEnviar();
        }}
      >
        <textarea
          className="defensia-chat-input"
          rows={2}
          placeholder="Escribe tu pregunta sobre el expediente…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={streaming}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleEnviar();
            }
          }}
        />
        <button
          type="submit"
          className="defensia-chat-send"
          disabled={streaming || text.trim().length === 0}
          aria-label="Enviar"
        >
          {streaming ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
          Enviar
        </button>
      </form>
    </div>
  );
}
