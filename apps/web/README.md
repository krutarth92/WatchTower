# WATCHTOWER web

The private SvelteKit interface for WATCHTOWER threat-intelligence research.

Run the locked development workflow from the repository root:

```powershell
pnpm install --frozen-lockfile
pnpm --dir apps/web dev --host 127.0.0.1
```

The application is available at `http://127.0.0.1:5173`. Configure its
server-side API origin with `WATCHTOWER_API_ORIGIN`; the value is never sent
to browser code.

All shared visual values live in `src/lib/styles/tokens.css`. Change colors,
type, spacing, radii, shadows, and motion there so the interface stays
consistent.

Run the complete frontend gate with:

```powershell
pnpm --dir apps/web format:check
pnpm --dir apps/web lint
pnpm --dir apps/web check
pnpm --dir apps/web test:unit
pnpm --dir apps/web build
pnpm --dir apps/web test:e2e
```
