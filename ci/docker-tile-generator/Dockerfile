ARG python3=mirror.gcr.io/python:3.11-slim-bookworm

FROM ${python3}

RUN apt-get update && \
    apt-get install --yes git wget zip && \
    rm -rf /var/lib/apt/lists/*

# Resolve the latest tag from the releases/latest redirect instead of the
# GitHub API, which rate-limits unauthenticated requests from shared CI IPs.
RUN BOSH_TAG="$(wget -S --spider --max-redirect=0 https://github.com/cloudfoundry/bosh-cli/releases/latest 2>&1 | sed -n 's#^ *Location: .*/releases/tag/\(v[^ ]*\).*#\1#p' | head -1)" && \
    test -n "${BOSH_TAG}" && \
    wget -q -O /usr/local/bin/bosh "https://github.com/cloudfoundry/bosh-cli/releases/download/${BOSH_TAG}/bosh-cli-${BOSH_TAG#v}-linux-amd64" && \
    chmod 755 /usr/local/bin/bosh && \
    bosh --version

RUN wget -q -O /tmp/cf.tgz https://packages.cloudfoundry.org/stable\?release\=linux64-binary\&version\=v8
RUN tar -C /tmp -zxf /tmp/cf.tgz
RUN mv /tmp/cf8 /usr/local/bin/cf8
RUN mv /tmp/cf /usr/local/bin/cf

COPY bundle*.tar.gz .
RUN tar -C /tmp -zxf bundle*.tar.gz
RUN mv /tmp/dist-*/tile_linux-64bit /usr/local/bin/tile
RUN mv /tmp/dist-*/pcf_linux-64bit /usr/local/bin/pcf
