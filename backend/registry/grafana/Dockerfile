# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
RUN apk add --no-cache curl tar
ARG VERSION=11.4.0
WORKDIR /src
RUN curl -sL https://github.com/grafana/grafana/archive/refs/tags/v${VERSION}.tar.gz -o grafana.tar.gz && \
    tar xzf grafana.tar.gz && \
    mv grafana-${VERSION} grafana

WORKDIR /src/grafana
RUN corepack enable && corepack prepare pnpm@latest --activate
RUN pnpm install --frozen-lockfile && pnpm build

# Stage 2: Build backend
FROM golang:1.23-alpine AS backend-builder
RUN apk add --no-cache curl tar build-base git
ARG VERSION=11.4.0
WORKDIR /src
RUN curl -sL https://github.com/grafana/grafana/archive/refs/tags/v${VERSION}.tar.gz -o grafana.tar.gz && \
    tar xzf grafana.tar.gz && \
    mv grafana-${VERSION} grafana

COPY --from=frontend-builder /src/grafana/public /src/grafana/public

WORKDIR /src/grafana
RUN mkdir -p /tmp/grafana-build && \
    go run build.go build && \
    cp bin/linux-amd64/grafana /tmp/grafana-build/ && \
    cp bin/linux-amd64/grafana-server /tmp/grafana-build/ && \
    cp -r conf /tmp/grafana-build/

# Stage 3: Runtime
FROM alpine:3.21
RUN apk add --no-cache ca-certificates tzdata curl

COPY --from=backend-builder /tmp/grafana-build /usr/share/grafana

RUN mkdir -p /var/lib/grafana /var/log/grafana /etc/grafana && \
    addgroup -S grafana && adduser -S -G grafana grafana && \
    chown -R grafana:grafana /usr/share/grafana /var/lib/grafana /var/log/grafana

ENV PATH=/usr/share/grafana/bin:$PATH \
    GF_PATHS_CONFIG=/etc/grafana/grafana.ini \
    GF_PATHS_DATA=/var/lib/grafana \
    GF_PATHS_LOGS=/var/log/grafana \
    GF_PATHS_PLUGINS=/var/lib/grafana/plugins

EXPOSE 3000
VOLUME ["/var/lib/grafana"]
USER grafana
ENTRYPOINT ["/usr/share/grafana/bin/grafana-server"]
CMD ["--homepath=/usr/share/grafana", "--config=/etc/grafana/grafana.ini"]
