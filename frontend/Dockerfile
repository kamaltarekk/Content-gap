FROM node:22-slim AS build
WORKDIR /app
RUN corepack enable
COPY package.json ./
RUN pnpm install --no-frozen-lockfile
COPY . .
RUN pnpm build

FROM node:22-slim AS runtime
WORKDIR /app
RUN corepack enable && pnpm add -g vite
COPY --from=build /app/dist ./dist
EXPOSE 5173
CMD ["vite", "preview", "--host", "0.0.0.0", "--port", "5173"]
