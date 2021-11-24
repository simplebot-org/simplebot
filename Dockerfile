FROM python:3.9-slim
RUN mkdir /app
WORKDIR /app
RUN apt-get update && apt-get install -y git && pip install --upgrade pip
COPY . /app
RUN pip install .
