# Stage 1: Source build from upstream
FROM ubuntu:24.04 AS builder
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake libncurses-dev libssl-dev libxml2-dev libkrb5-dev \
    libcurl4-openssl-dev bison flex libfmt-dev libpcre3-dev zlib1g-dev \
    libsystemd-dev curl ca-certificates tar pkg-config && \
    rm -rf /var/lib/apt/lists/*

ARG VERSION=10.6.20
ARG CMAKE_FLAGS="-DCMAKE_BUILD_TYPE=Release -DWITH_UNIT_TESTS=OFF -DWITHOUT_MROONGA=1 -DWITHOUT_TOKUDB=1 -DWITH_READLINE=ON -DWITH_SSL=system -DWITH_ZLIB=system -DWITH_LZ4=OFF"

WORKDIR /src
RUN curl -sL "https://github.com/MariaDB/server/archive/refs/tags/mariadb-${VERSION}.tar.gz" -o mariadb.tar.gz && \
    tar xzf mariadb.tar.gz && \
    mv "server-mariadb-${VERSION}" mariadb

WORKDIR /src/mariadb/build
RUN cmake .. ${CMAKE_FLAGS} && \
    make -j$(nproc) && \
    make install DESTDIR=/tmp/mariadb-install

# Stage 2: Minimal runtime
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libncurses6 libssl3 libxml2 libcurl4 libfmt10 libpcre3 libkrb5-3 \
    ca-certificates tzdata && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r mysql && useradd -r -g mysql mysql && \
    mkdir -p /var/lib/mysql /var/run/mysqld && \
    chown -R mysql:mysql /var/lib/mysql /var/run/mysqld

COPY --from=builder /tmp/mariadb-install/usr/local/mysql/ /usr/local/mysql/
COPY --from=builder /tmp/mariadb-install/usr/local/mysql/bin/ /usr/local/bin/

RUN ln -sf /usr/local/mysql/bin/mysqld /usr/local/bin/mysqld && \
    ln -sf /usr/local/mysql/bin/mysql /usr/local/bin/mysql && \
    ln -sf /usr/local/mysql/bin/mysqladmin /usr/local/bin/mysqladmin

VOLUME ["/var/lib/mysql"]
EXPOSE 3306

USER mysql
CMD ["mysqld", "--user=mysql", "--datadir=/var/lib/mysql"]
