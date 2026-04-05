FROM node:20-alpine

WORKDIR /app

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml turbo.json ./
COPY apps/content-verification-service ./apps/content-verification-service
COPY packages/kafka ./packages/kafka
COPY packages/typescript-config ./packages/typescript-config

RUN corepack enable && pnpm install --filter content-verification-service... --frozen-lockfile

EXPOSE 8082

CMD ["pnpm", "--filter", "content-verification-service", "dev"]
