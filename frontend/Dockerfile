# syntax=docker/dockerfile:1

# --- Стадия сборки фронтенда ---
FROM node:22-alpine AS build
WORKDIR /app
ENV NODE_OPTIONS=--max-old-space-size=2048
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm npm ci --prefer-offline --no-audit || npm install
COPY . .
# В образе выполняем только сборку Vite (без tsc — типизация проверяется в dev/CI);
# кэш Vite ускоряет повторные сборки.
RUN --mount=type=cache,target=/root/.npm --mount=type=cache,target=/app/node_modules/.vite \
    npx vite build

# --- Стадия раздачи через nginx ---
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
