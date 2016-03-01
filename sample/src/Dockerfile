FROM alpine

RUN apk add --no-cache zip &&\
    apk add --no-cache python && \
    apk add --no-cache --virtual=build-dependencies wget ca-certificates && \
    wget "https://bootstrap.pypa.io/get-pip.py" -O /dev/stdout | python && \
    apk del build-dependencies

ADD app/app.py .
ADD app/requirements.txt .
RUN pip install -r requirements.txt

CMD python app.py