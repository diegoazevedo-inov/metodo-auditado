import React from "react";

// Tela legada, anterior a migracao responsiva. A divida aqui e conhecida e
// esta congelada na baseline da catraca; ela nao pode crescer.
export function RelatorioLegado({ linhas }: any) {
  return (
    <div className="p-4">
      <div className="w-[720px] rounded border border-border">
        <table className="text-sm">
          <thead>
            <tr>
              <th className="whitespace-nowrap px-2">Nome</th>
              <th className="whitespace-nowrap px-2">Valor</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l: any) => (
              <tr key={l.id}>
                <td className="whitespace-nowrap px-2">{l.nome}</td>
                <td className="whitespace-nowrap px-2 tabular-nums">{l.valor}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="truncate text-sm text-muted-foreground">{linhas.length} registros</p>
    </div>
  );
}
