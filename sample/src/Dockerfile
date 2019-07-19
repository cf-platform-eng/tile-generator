FROM python:3-slim

RUN apt-get update && apt-get install --yes zip

ADD app/app.py .
ADD app/requirements.txt .
RUN pip install -r requirements.txt

CMD python app.py