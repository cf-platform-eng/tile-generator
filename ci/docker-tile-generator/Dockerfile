FROM alpine

RUN apk --update upgrade && \
    apk add --update ca-certificates && \
    update-ca-certificates && \
    apk add --update openssl && \
    rm -rf /var/cache/apk/*

RUN apk add --no-cache zip &&\
    apk add --no-cache python && \
    apk add --no-cache jq && \
    apk add --no-cache --virtual=build-dependencies wget ca-certificates && \
    wget "https://bootstrap.pypa.io/get-pip.py" -O /dev/stdout | python && \
    apk del build-dependencies


RUN wget https://github.com/cloudfoundry/bosh-cli/releases/download/v5.5.0/bosh-cli-5.5.0-linux-amd64
RUN mv bosh-cli-5.5.0-linux-amd64 /usr/local/bin/bosh
RUN chmod 755 /usr/local/bin/bosh

RUN wget -O /tmp/cf.tgz https://packages.cloudfoundry.org/stable?release=linux64-binary
RUN tar -C /tmp -zxf /tmp/cf.tgz
RUN mv /tmp/cf /usr/local/bin/cf

RUN apk add --update git
RUN apk add --update bash
RUN apk add --update openssh-client

RUN rm -rf /var/cache/apk/*

COPY tile-generator-*.tar.gz .
RUN pip install tile-generator-*.tar.gz
