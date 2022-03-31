FROM python:3.10

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY ./etc/logging.yml ./etc/logging.yml
COPY ./src ./src
COPY ./tools ./tools

ENV PYTHONPATH "/app/src"

EXPOSE 8000
