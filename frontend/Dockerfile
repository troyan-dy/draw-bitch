FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* .npmrc* ./
RUN npm ci || npm install

FROM node:22-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-slim AS run
WORKDIR /app
ENV NODE_ENV=production
# server.js слушает этот адрес/порт (иначе standalone биндится на localhost
# и снаружи контейнера недоступен).
ENV HOSTNAME=0.0.0.0 PORT=3000
# Standalone output: сам сервер + трассированные зависимости, статика и public.
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
