ARG VARIANT=3.12.7
FROM python:${VARIANT}

WORKDIR /usr/src/app

COPY . .