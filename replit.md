# MoJiTo TV Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Artifacts

### MoJiTo TV (`artifacts/mojito-tv`)
- React + Vite frontend TV streaming interface
- Compatible with Chrome 46+ (pure inline styles, no CSS variables, no Grid)
- TV view: channel list, video player, keyboard nav (arrows/enter/esc)
- Dashboard view: stats and channel overview
- Data from GitHub raw JSON files: `working_streams.json`

### API Server (`artifacts/api-server`)
- Express 5 backend
- `/api/mojito/tv` — channel list (fetched from MoJiTo GitHub repo)
- `/api/mojito/stats` — stream/cluster stats
- `/api/mojito/channels` — channel list with limit
- `/api/mojito/play/:id` — get stream URL for channel
- Data cached from `https://raw.githubusercontent.com/mojitopro/MoJiTo/main/working_streams.json`

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
