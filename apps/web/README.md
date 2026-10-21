# WATCHTOWER web

The private SvelteKit interface for WATCHTOWER threat-intelligence research.

Run commands from the repository root:

```powershell
pnpm install
pnpm web:dev
```

The application is available at `http://127.0.0.1:5173`. Configure its
server-side API origin with `WATCHTOWER_API_ORIGIN`; the value is never sent
to browser code.

All shared visual values live in `src/lib/styles/tokens.css`. Change colors,
type, spacing, radii, shadows, and motion there so the interface stays
consistent.
