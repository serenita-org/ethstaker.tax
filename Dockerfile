FROM python:3.10@sha256:817c0d8684087acb6d88f0f0951f9a541aa3e762302aa5e8f439d5d12edd48ad

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --no-deps --use-deprecated=legacy-resolver -r requirements.txt

COPY ./etc/logging.yml ./etc/logging.yml
COPY ./src ./src
COPY ./tools ./tools

ENV PYTHONPATH "/app/src"

EXPOSE 8000
