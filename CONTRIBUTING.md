# Contributing to invAIriant

Single maintainer: **[@mindicator](https://github.com/mindicator)**.
Documentation authorship is credited as **mindicator & silicon bags quartet**.

This project practices what it audits, so its contribution rules are short and
enforced by the framework's own checks.

## Definition of done for a change

- **Self-validation passes.** `scripts/validate_framework.py` is green: all
  JSON schemas parse, example configs validate against
  `schemas/invairiant.config.schema.json`, the example findings validate
  against `schemas/finding.schema.json`, and every lens file carries the
  required sections. CI runs this as
  [`.github/workflows/validate.yml`](.github/workflows/validate.yml).
- **Lens files keep the canonical structure.** New or edited lenses preserve
  the section order and the verbatim 0–10 scoring rubric (see any file under
  [`lenses/`](lenses/) and the writing guide in
  [docs/lens-taxonomy.md](docs/lens-taxonomy.md)).
- **The protocol's own rules hold in the text.** No lens or template weakens
  "no evidence, no finding," the anti-averaging rule, or the
  observation/finding separation.

## Scope of changes

- **New lenses** go in the right pack with a kebab-case id; cross-listed
  lenses get a stub, never a fork ([docs/lens-taxonomy.md](docs/lens-taxonomy.md)).
- **Schema changes** are contracts — bump thoughtfully; the schemas are the
  stable interface other tooling depends on.
- **the origin project-specific material** stays out of the generic core; domain
  judgment belongs in [`lenses/domain/`](lenses/domain/).

## Reporting issues

Open a GitHub issue with concrete evidence — the same standard the protocol
sets for findings. "This feels off" is an observation; a file/line, a failing
check, or a doc/code contradiction is a report that can be acted on.

## License

By contributing you agree that your contributions are licensed under
[Apache-2.0](LICENSE).
