FROM python:2

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install bundler pandoc ruby zip
RUN gem install bosh_cli --no-ri --no-rdoc

ADD requirements.txt .
RUN pip install -r requirements.txt
