FROM node:20-alpine

WORKDIR /app

ENV NODE_ENV=production

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml turbo.json ./
COPY apps/kafka-service ./apps/kafka-service
COPY packages/kafka ./packages/kafka
COPY packages/typescript-config ./packages/typescript-config

RUN corepack enable && pnpm install --filter kafka-service... --frozen-lockfile

RUN addgroup -S app && adduser -S app -G app
USER app

EXPOSE 8081

CMD ["pnpm", "--filter", "kafka-service", "start"]
