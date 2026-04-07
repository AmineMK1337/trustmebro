# Context Verification Service

Next.js service that provides the context-verification web experience and API route for post/context checks.

## Role In The Architecture

- Public service exposed on port 3000
- Hosts UI and `/api/verify`
- Complements source verification by checking context consistency
- Integrates with Gemini, reverse image lookup, and linked-article extraction

## Local Development

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Required Environment Variables

- GEMINI_API_KEY
- IMGBB_API_KEY
- SERPAPI_API_KEY

## Related Services

- Source scoring and adaptive policy flow: [../source-verification-service/README.md](../source-verification-service/README.md)
- RL architecture details for source scoring: [../source-verification-service/RL.md](../source-verification-service/RL.md)
