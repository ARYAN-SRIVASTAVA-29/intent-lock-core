# IntentLock 0.9 verification

- Backend: `39 passed`
- Inventory commit: verified on successful payment
- Inventory idempotency: verified across authorization, capture, and repeated capture events
- Inventory release: verified after authorized payment failure
- Dashboard operational analytics: verified from persisted data
- TypeScript: `pnpm exec tsc --noEmit --pretty false` passed
- Production build: `pnpm build` passed
- Landing page and onboarding source were not redesigned

The supervised cloud preview cannot launch this repository's native Next.js development command because that preview forwards Vite-only flags. The production build and automated validation pass; run the included release locally with the normal `npm run dev` and FastAPI commands.
