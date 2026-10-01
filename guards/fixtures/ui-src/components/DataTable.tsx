import React from "react";

// Componente-padrao de tabela do projeto: e ele que oferece a contencao
// de rolagem horizontal. Este arquivo e isento da regra 1 do GUARD 2.
export function DataTable({ children }: { children: React.ReactNode }) {
  return (
    <div className="w-full overflow-x-auto rounded-md border border-border">
      <table className="w-full text-sm text-foreground">{children}</table>
    </div>
  );
}
