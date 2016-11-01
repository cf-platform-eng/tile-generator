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

RUN apk add --no-cache ruby ruby-bundler

RUN gem install bosh_cli --no-ri --no-rdoc

RUN apk add --update bash
RUN apk add --update openssh-client

RUN rm -rf /var/cache/apk/*
