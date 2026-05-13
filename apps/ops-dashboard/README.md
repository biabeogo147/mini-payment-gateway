# Ops Dashboard Scaffold

This app is the route-first scaffold prepared ahead of phase 10.

What is ready here:

- React + Vite + TypeScript app structure
- workspace wiring from the repository root
- env template for local API wiring
- shared app shell and planned navigation
- placeholder pages for the phase 10 feature areas

What is intentionally not implemented yet:

- internal auth
- RBAC
- API integration
- tables, filters, charts, and operator workflows backed by real data

Local commands from the repository root:

```bash
npm install
npm run ops-dashboard:dev
```

Then open the Vite local URL shown in the terminal.

Local env setup:

```bash
copy apps\\ops-dashboard\\.env.example apps\\ops-dashboard\\.env.local
```
