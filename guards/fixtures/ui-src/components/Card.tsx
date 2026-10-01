import React from "react";
import { BrandLogoMark } from "./BrandLogoMark";

export function Card({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-lg bg-card text-card-foreground p-4 shadow-sm">
      <header className="flex items-center gap-2 border-b border-border pb-2">
        <BrandLogoMark />
        <h2 className="text-base font-medium text-foreground">{title}</h2>
      </header>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
      <a className="mt-3 inline-block text-sm text-primary" href="#detalhes">
        ver detalhes
      </a>
    </section>
  );
}
