import React from "react";
import { Card } from "./components/Card";
import { Toolbar } from "./components/Toolbar";

const DOCS = "https://exemplo.invalid/docs#fa0";

export function App() {
  return (
    <main className="min-h-dvh bg-background text-foreground">
      <Toolbar onSave={() => {}} onClose={() => {}} busy={false} />
      <Card title="Resumo" body="Conteudo do cartao" />
      <a href={DOCS} className="text-sm text-primary">documentacao</a>
    </main>
  );
}
