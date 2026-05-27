# Stage 1: Download official ClickHouse binary artifacts
# ClickHouse собирается из исходников (cmake/ninja), официальные бинарные сборки
# распространяются через packages.clickhouse.com
FROM alpine:3.21 AS builder
RUN apk add --no-cache curl tar ca-certificates

ARG VERSION=24.3.12.72

WORKDIR /opt
RUN curl -fsSL "https://packages.clickhouse.com/tgz/stable/clickhouse-common-static-${VERSION}-amd64.tgz" -o clickhouse.tgz && \
    tar xzf clickhouse.tgz && \
    mv "clickhouse-common-static-${VERSION}" clickhouse-common && \
    curl -fsSL "https://packages.clickhouse.com/tgz/stable/clickhouse-server-${VERSION}-amd64.tgz" -o server.tgz && \
    tar xzf server.tgz && \
    mv "clickhouse-server-${VERSION}" clickhouse-server

# Stage 2: Minimal runtime
FROM alpine:3.21
RUN apk add --no-cache ca-certificates tzdata su-exec && \
    addgroup -S clickhouse && adduser -S -G clickhouse clickhouse

COPY --from=builder /opt/clickhouse-common/usr/bin/clickhouse /usr/bin/clickhouse
COPY --from=builder /opt/clickhouse-server/etc/clickhouse-server/ /etc/clickhouse-server/
COPY --from=builder /opt/clickhouse-server/usr/bin/clickhouse-server /usr/bin/
COPY --from=builder /opt/clickhouse-server/usr/bin/clickhouse-client /usr/bin/

RUN ln -sf /usr/bin/clickhouse /usr/bin/clickhouse-cli && \
    mkdir -p /var/lib/clickhouse /var/log/clickhouse-server && \
    chown -R clickhouse:clickhouse /var/lib/clickhouse /var/log/clickhouse-server

VOLUME ["/var/lib/clickhouse"]
EXPOSE 8123 9000

USER clickhouse
CMD ["clickhouse-server", "--config-file=/etc/clickhouse-server/config.xml"]
