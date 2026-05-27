# Stage 1: Base PHP image with dependencies
FROM php:8.3-fpm-alpine AS builder
RUN apk add --no-cache bash curl tar bzip2 nginx libpng-dev libzip-dev

ARG VERSION=30.0.0

# Install PHP extensions
RUN docker-php-ext-install -j$(nproc) gd zip pdo_mysql pdo_pgsql pgsql opcache exif

WORKDIR /var/www
RUN curl -sL https://download.nextcloud.com/server/releases/nextcloud-${VERSION}.tar.bz2 -o nextcloud.tar.bz2 && \
    tar xf nextcloud.tar.bz2 && \
    mv nextcloud html && \
    chown -R www-data:www-data html

# Configure PHP for Nextcloud
RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" && \
    echo 'upload_max_filesize=10G' >> /usr/local/etc/php/conf.d/nextcloud.ini && \
    echo 'post_max_size=10G' >> /usr/local/etc/php/conf.d/nextcloud.ini && \
    echo 'memory_limit=512M' >> /usr/local/etc/php/conf.d/nextcloud.ini && \
    echo 'max_execution_time=3600' >> /usr/local/etc/php/conf.d/nextcloud.ini

# Stage 2: Runtime
FROM php:8.3-fpm-alpine
RUN apk add --no-cache nginx bash libzip libpng libpq curl tzdata && \
    addgroup -S nextcloud && adduser -S -G nextcloud www-data

COPY --from=builder /var/www /var/www
COPY --from=builder /usr/local/etc/php/conf.d/nextcloud.ini /usr/local/etc/php/conf.d/nextcloud.ini

RUN mkdir -p /var/log/nginx /var/run/nginx /var/tmp/nginx && \
    chown -R www-data:www-data /var/www /var/log/nginx /var/run/nginx /var/tmp

EXPOSE 80
VOLUME ["/var/www/html/data", "/var/www/html/config"]
CMD ["php-fpm"]
