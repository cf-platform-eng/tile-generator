FROM python:3-slim

RUN apt-get update && \
    apt-get install --yes git wget zip && \
    rm -rf /var/lib/apt/lists/*

RUN wget -q -O- https://api.github.com/repos/cloudfoundry/bosh-cli/releases/latest | grep 'browser_download_url.*linux-amd64' | cut -d '"' -f 4 | xargs wget -q
RUN mv bosh-cli-*-linux-amd64 /usr/local/bin/bosh
RUN chmod 755 /usr/local/bin/bosh

RUN wget -q -O /tmp/cf.tgz https://packages.cloudfoundry.org/stable?release=linux64-binary
RUN tar -C /tmp -zxf /tmp/cf.tgz
RUN mv /tmp/cf /usr/local/bin/cf

COPY bundle*.tar.gz .
RUN tar -C /tmp -zxf bundle*.tar.gz
RUN mv /tmp/dist-*/tile_linux-64bit /usr/local/bin/tile
RUN mv /tmp/dist-*/pcf_linux-64bit /usr/local/bin/pcf
