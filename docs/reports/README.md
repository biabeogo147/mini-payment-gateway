# Reports

This folder contains the academic project report and the companion API
documentation for the Mini Payment Gateway.

## Documents

- `main.tex`
  - academic project report
  - narrative-focused
  - exactly 10 required chapters
- `api-documentation.tex`
  - companion API reference
  - contract-focused
  - reuses the same API IDs as the report, API markdown docs, and Postman

## Structure

- `shared/`
  - common metadata, LaTeX packages, macros, and title-page helpers
- `chapters/`
  - main report chapter files
- `api-sections/`
  - companion API documentation sections
- `appendices/`
  - report appendices such as demo storyline and future work
- `figures/`
  - screenshots and diagrams used by both documents

## Build

From `docs/reports`:

```bash
mkdir -p build
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build api-documentation.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build api-documentation.tex
```

The repeated pass resolves the table of contents, figure numbering, and table
numbering cleanly.

## Source Of Truth Map

| Report area | Primary sources |
| --- | --- |
| System requirements, use cases, user stories | `docs/product/` |
| System and component architecture | `docs/architecture/`, `docs/product/modules-and-entities.md`, `docs/product/state-machine.md` |
| Database design | `docs/product/modules-and-entities.md`, `backend/app/models/`, `backend/alembic/versions/` |
| User interface design | `docs/product/ui-design.md`, `apps/ops-dashboard/`, `apps/merchant-dashboard/` |
| API design and implementation | `docs/api/`, `backend/app/controllers/`, `backend/app/schemas/` |
| Testing and evaluation | `docs/testing/`, `backend/tests/`, `docs/history/completions/` |
| High-level deployment overview | `docs/infrastructure/devops-architecture.md` only |

## Boundary Rules

- `main.tex` explains system intent, design, and implemented behavior at report
  level.
- `api-documentation.tex` owns the detailed API contract blocks.
- Do not repeat full request/response contracts inside the report unless a short
  example is needed for design explanation.
- Do not pull long historical rollout notes into either document.
- Do not document features that are not implemented in the current repo.
