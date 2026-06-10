FROM node:20-bookworm-slim AS build

RUN corepack enable

WORKDIR /app/frontend

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend /app/frontend

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN pnpm build


FROM node:20-bookworm-slim AS runtime

RUN npm install --global serve@14.2.4

WORKDIR /app/frontend

COPY --from=build /app/frontend/dist ./dist

EXPOSE 4173

CMD ["sh", "-c", "exec serve -s dist -l tcp://0.0.0.0:${PORT:-4173}"]
