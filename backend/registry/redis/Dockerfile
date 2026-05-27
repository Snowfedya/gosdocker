# Stage 1: Source build from upstream
FROM alpine:3.21 AS builder
RUN apk add --no-cache build-base linux-headers curl tar

ARG VERSION=7.2.7

WORKDIR /src
RUN curl -sL "https://github.com/redis/redis/archive/refs/tags/${VERSION}.tar.gz" -o redis.tar.gz && \
    tar xzf redis.tar.gz && \
    mv "redis-${VERSION}" redis

WORKDIR /src/redis
RUN make -j$(nproc) && \
    make install PREFIX=/usr/local/redis

# Stage 2: Minimal runtime
FROM alpine:3.21
RUN apk add --no-cache ca-certificates tzdata su-exec && \
    addgroup -S redis && adduser -S -G redis redis

COPY --from=builder /usr/local/redis/bin/redis-server /usr/local/bin/
COPY --from=builder /usr/local/redis/bin/redis-cli /usr/local/bin/
COPY --from=builder /usr/local/redis/bin/redis-sentinel /usr/local/bin/
COPY --from=builder /usr/local/redis/bin/redis-benchmark /usr/local/bin/
COPY --from=builder /usr/local/redis/bin/redis-check-aof /usr/local/bin/
COPY --from=builder /usr/local/redis/bin/redis-check-rdb /usr/local/bin/

RUN mkdir -p /data && chown -R redis:redis /data

VOLUME ["/data"]
EXPOSE 6379

USER redis
CMD ["redis-server", "--protected-mode", "no"]
