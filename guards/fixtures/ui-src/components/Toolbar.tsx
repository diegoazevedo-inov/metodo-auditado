import React from "react";

export function Toolbar({ onSave, onClose, busy }: any) {
  return (
    <div className="flex items-center justify-between gap-2 bg-background p-2">
      <button
        type="button"
        onClick={onSave}
        className={busy ? "bg-muted text-muted-foreground" : "bg-primary text-primary-foreground"}
      >
        Salvar
      </button>
      <button
        type="button"
        aria-label="Fechar"
        onClick={onClose}
        className="h-8 w-8 grid place-items-center rounded text-brand"
      >
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 2l12 12" /></svg>
      </button>
      <span className="rounded border border-brand px-2 py-1 text-xs text-foreground">
        rascunho
      </span>
    </div>
  );
}
