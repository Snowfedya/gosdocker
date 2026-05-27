# Stage 1: Source build
FROM alpine:3.21 AS builder
RUN apk add --no-cache build-base pcre-dev openssl-dev zlib-dev linux-headers curl tar

ARG VERSION=1.27.4

WORKDIR /src
RUN curl -sL https://nginx.org/download/nginx-${VERSION}.tar.gz -o nginx.tar.gz && \
    tar xzf nginx.tar.gz && \
    cd nginx-${VERSION} && \
    ./configure \
        --prefix=/etc/nginx \
        --sbin-path=/usr/sbin/nginx \
        --modules-path=/usr/lib/nginx/modules \
        --conf-path=/etc/nginx/nginx.conf \
        --error-log-path=/var/log/nginx/error.log \
        --http-log-path=/var/log/nginx/access.log \
        --pid-path=/var/run/nginx.pid \
        --lock-path=/var/run/nginx.lock \
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
    mkdir -p /usr/lib/nginx/modules

# Stage 2: Minimal runtime
FROM alpine:3.21
RUN apk add --no-cache ca-certificates curl tzdata && \
    addgroup -S nginx && adduser -S -G nginx nginx

COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx
COPY --from=builder /etc/nginx /etc/nginx
COPY --from=builder /usr/lib/nginx/modules /usr/lib/nginx/modules

RUN mkdir -p /var/log/nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx /var/cache/nginx /etc/nginx && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

EXPOSE 80 443
STOPSIGNAL SIGTERM
CMD ["nginx", "-g", "daemon off;"]
