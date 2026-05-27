# Stage 1: Go build
FROM golang:1.23-alpine AS builder
RUN apk add --no-cache git make build-base curl tar

ARG VERSION=2.55.0

WORKDIR /src
RUN curl -sL https://github.com/prometheus/prometheus/archive/refs/tags/v${VERSION}.tar.gz -o prometheus.tar.gz && \
    tar xzf prometheus.tar.gz && \
    mv prometheus-${VERSION} prometheus

WORKDIR /src/prometheus
RUN mkdir -p data && \
    make build && \
    cp prometheus /tmp/prometheus && \
    cp promtool /tmp/promtool

# Stage 2: Minimal scratch runtime
FROM alpine:3.21
RUN apk add --no-cache ca-certificates tzdata wget

COPY --from=builder /tmp/prometheus /bin/prometheus
COPY --from=builder /tmp/promtool /bin/promtool

RUN mkdir -p /prometheus /etc/prometheus && \
    addgroup -S prometheus && adduser -S -G prometheus prometheus && \
    chown -R prometheus:prometheus /prometheus /etc/prometheus

VOLUME ["/prometheus", "/etc/prometheus"]
EXPOSE 9090
USER prometheus
ENTRYPOINT ["/bin/prometheus"]
CMD ["--config.file=/etc/prometheus/prometheus.yml", "--storage.tsdb.path=/prometheus", "--web.console.libraries=/etc/prometheus/console_libraries", "--web.console.templates=/etc/prometheus/consoles", "--storage.tsdb.retention.time=15d"]
