# Stage 1: Source build (PostgreSQL 17 — для РЕД ОС)
FROM debian:bookworm-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libreadline-dev zlib1g-dev libxml2-dev libssl-dev libicu-dev liblz4-dev \
    ca-certificates wget && \
    rm -rf /var/lib/apt/lists/*

ARG VERSION=17.2

WORKDIR /src
RUN wget -q https://ftp.postgresql.org/pub/source/v${VERSION}/postgresql-${VERSION}.tar.bz2 && \
    tar xf postgresql-${VERSION}.tar.bz2 && \
    cd postgresql-${VERSION} && \
    ./configure \
        --prefix=/usr/local/pgsql \
        --with-openssl \
        --with-icu \
        --with-readline \
        --with-libxml \
        --with-lz4 && \
    make -j$(nproc) world && \
    make install-world

# Stage 2: Minimal runtime
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreadline8 libxml2 libicu72 libssl3 liblz4-1 ca-certificates tzdata && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r postgres && useradd -r -g postgres postgres

COPY --from=builder /usr/local/pgsql /usr/local/pgsql
RUN mkdir -p /var/lib/postgresql/data /var/run/postgresql && \
    chown -R postgres:postgres /var/lib/postgresql /var/run/postgresql && \
    echo 'host all all 0.0.0.0/0 md5' >> /usr/local/pgsql/share/pg_hba.conf.sample

ENV PATH=/usr/local/pgsql/bin:$PATH \
    PGDATA=/var/lib/postgresql/data \
    PG_VERSION=17

EXPOSE 5432
STOPSIGNAL SIGINT
USER postgres
CMD ["postgres", "-D", "/var/lib/postgresql/data"]
