ARG python3=mirror.gcr.io/python:3-slim

FROM ${python3}

RUN apt-get update && apt-get install --yes zip

# Use Broadcom internal VCFD Artifactory for security compliance
ARG PIP_INDEX_URL=https://packages.vcfd.broadcom.net/artifactory/api/pypi/pypi-virtual/simple
ENV PIP_INDEX_URL="${PIP_INDEX_URL}"

ADD app/app.py .
ADD app/requirements.txt .
RUN pip install -r requirements.txt

CMD python app.py