# Método Auditado — English summary

A method for building software with agentic systems without relying on what
the system says about its own work. It rests on three rules: the one who
implements does not audit, no decision is made without measurement, and no
checker is put to use before it catches a defect planted on purpose.

It covers two cases: recovering a project that has already built up technical
debt, and starting a new project without building it up.

The full method is in Portuguese: [METODO.md](METODO.md) is the core text, and
the [main README](README.md) maps the rest of the repository.

## The problem

An agentic system delivers the artifact and, with it, the claim that the
artifact is correct. The two are not the same thing: a convincing summary does
not guarantee correct code. The method exists so that the gap between what was
reported and what was done shows up during development, not in production.

## Principles

**The one who implements does not audit.** Three roles, never in the same
session: the one who plans and audits, the one who executes, and the owner, who
decides and has every decision recorded. The audit does not accept the
delivery report as evidence: it runs the proofs again. The audit can be wrong
too, which is why the executor may contest it, with proof.

**Measure before giving an opinion.** Every phase starts with a reproducible
measurement. The number becomes the plan's target and the scoreboard that the
following phases bring to zero.

**Plant a defect before trusting a check.** A checker that has never failed has
not proven that it works. Before using it, plant the defect it is supposed to
catch and confirm that it fails.

**A green proof does not validate its premise.** A passing suite can be proving
the wrong thing. A test that accepts an intermediate state stays green even
when the final result never happens, like a service worker that never
installs. The assertion has to require the final state.

## The four axes

1. **Light and dark theme**: colors only through semantic tokens, contrast
   computed against WCAG, and a palette checker.
2. **Navigation flows**: going back without losing context, with filters and
   state in the URL.
3. **Responsive layout**: a layout template, a sweep across screen sizes, and a
   ratchet that keeps the debt from growing.
4. **PWA**: a cache that never stores authenticated data, a service worker
   whose installation is proven, and a manifest that follows the theme.

Each axis comes with a measured audit recipe, phases with acceptance criteria,
prompt templates for executor and auditor, and what stays after the fix: the
checkers and specifications that keep the debt from coming back.

The six UI checkers are in [guards/](guards/), each with the proof that plants
its defects.

## Results

In the method's first full application, on a production web app:

- **Responsive layout:** from 60 routes with layout overflow to zero, proven by
  a reproducible signature.
- **Theme:** from 6,606 hardcoded colors to zero, with two themes and validated
  contrast.
- **Navigation:** from 93% broken to navigation that keeps its context.
- **PWA:** from an install that did not work to Lighthouse 100 in production.

Along the way: 12 adversarial audit reports and 3 real product defects found.

## License

Apache 2.0. See [LICENSE](LICENSE).
