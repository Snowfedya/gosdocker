# syntax=docker/dockerfile:1.6
# Two-stage build:
#   - builder: install deps and run `npm run build` to produce dist/
#   - runtime: nginx:alpine serving the dist/ directory
#
# AC-FRONTEND-BUILD: prior versions assumed a pre-built dist/ was committed
# to the repo, which led to stale frontend assets being served after a code
# change (e.g. the PortConflictError arity fix in useApi.ts did not reach
# the browser because dist/ had not been rebuilt). This Dockerfile now
# rebuilds on every `docker compose build frontend`.
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
