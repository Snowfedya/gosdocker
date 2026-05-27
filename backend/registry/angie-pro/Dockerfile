# Stage 1: Source build
FROM alpine:3.21 AS builder
RUN apk add --no-cache build-base pcre-dev openssl-dev zlib-dev linux-headers curl tar git

ARG VERSION=1.10.0

WORKDIR /src
RUN curl -sL https://github.com/angie/angie/archive/refs/tags/${VERSION}.tar.gz -o angie.tar.gz && \
    tar xzf angie.tar.gz && \
    cd angie-${VERSION} && \
    ./configure \
        --prefix=/etc/angie \
        --sbin-path=/usr/sbin/angie \
        --modules-path=/usr/lib/angie/modules \
        --conf-path=/etc/angie/angie.conf \
        --error-log-path=/var/log/angie/error.log \
        --http-log-path=/var/log/angie/access.log \
        --pid-path=/var/run/angie.pid \
        --lock-path=/var/run/angie.lock \
        --with-http_ssl_module \
        --with-http_v2_module \
        --with-http_gzip_static_module \
        --with-http_realip_module \
        --with-http_stub_status_module \
        --with-pcre \
        --with-file-aio \
        --with-threads && \
    make -j$(nproc) && \
    make install && \
    mkdir -p /usr/lib/angie/modules

# Stage 2: Minimal runtime
FROM alpine:3.21
RUN apk add --no-cache ca-certificates curl tzdata && \
    addgroup -S angie && adduser -S -G angie angie

COPY --from=builder /usr/sbin/angie /usr/sbin/angie
COPY --from=builder /etc/angie /etc/angie
COPY --from=builder /usr/lib/angie/modules /usr/lib/angie/modules
RUN mkdir -p /var/log/angie /var/cache/angie && \
    chown -R angie:angie /var/log/angie /var/cache/angie /etc/angie && \
    ln -sf /dev/stdout /var/log/angie/access.log && \
    ln -sf /dev/stderr /var/log/angie/error.log

EXPOSE 80 443
STOPSIGNAL SIGTERM
CMD ["angie", "-g", "daemon off;"]
