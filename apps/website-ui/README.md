# Website UI

Next.js frontend for TrustMeBro web experiences.

## Role In The Architecture

- User-facing web interface layer
- Works alongside backend verification services
- Complements source verification, which now uses adaptive policy-driven scoring

## Local Development

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Related Architecture Docs

- Monorepo architecture: [../../README.md](../../README.md)
- Source verification service: [../source-verification-service/README.md](../source-verification-service/README.md)
- Source adaptive RL details: [../source-verification-service/RL.md](../source-verification-service/RL.md)
