FROM python:2.7

ADD requirements.txt .
RUN apt-get update
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN gem install bosh_cli --no-ri --no-rdoc