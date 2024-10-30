FROM python:3.10@sha256:fd0fa50d997eb56ce560c6e5ca6a1f5cf8fdff87572a16ac07fb1f5ca01eb608

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --no-deps --use-deprecated=legacy-resolver -r requirements.txt

COPY ./etc/logging.yml ./etc/logging.yml
COPY ./src ./src
COPY ./tools ./tools

ENV PYTHONPATH "/app/src"

EXPOSE 8000
