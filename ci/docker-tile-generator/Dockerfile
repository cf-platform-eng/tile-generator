FROM alpine

RUN apk --update upgrade && \
    apk add --update ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/cache/apk/*

RUN apk add --no-cache zip &&\
    apk add --no-cache python && \
    apk add --no-cache --virtual=build-dependencies wget ca-certificates && \
    wget "https://bootstrap.pypa.io/get-pip.py" -O /dev/stdout | python && \
    apk del build-dependencies

COPY tile-generator-*.tar.gz .
RUN pip install tile-generator-*.tar.gz

RUN wget https://s3.amazonaws.com/bosh-cli-artifacts/bosh-cli-2.0.23-linux-amd64
RUN mv bosh-cli-2.0.23-linux-amd64 /usr/local/bin/bosh
RUN chmod 755 /usr/local/bin/bosh

RUN apk add --update git
RUN apk add --update bash
RUN apk add --update openssh-client

RUN rm -rf /var/cache/apk/*
