FROM python:3.9-slim
RUN mkdir /app
WORKDIR /app
RUN apt-get update && apt-get install -y git && pip install --upgrade pip
ADD requirements/requirements.txt /app
RUN pip install -r requirements.txt
COPY . /app
RUN pip install .
