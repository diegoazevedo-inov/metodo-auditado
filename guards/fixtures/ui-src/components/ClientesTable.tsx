import React from "react";
import { DataTable } from "./DataTable";

export function ClientesTable({ rows }: any) {
  return (
    <DataTable>
      <thead>
        <tr>
          <th className="whitespace-nowrap px-3 py-2 text-left">Nome</th>
          <th className="whitespace-nowrap px-3 py-2 text-left">Data</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r: any) => (
          <tr key={r.id} className="border-b border-border">
            <td className="px-3 py-2 text-foreground">{r.nome}</td>
            <td className="whitespace-nowrap px-3 py-2 tabular-nums">{r.data}</td>
          </tr>
        ))}
      </tbody>
    </DataTable>
  );
}
