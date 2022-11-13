FROM python:3.11-slim-buster as builder

WORKDIR /usr/src/app

RUN pip install poetry

COPY ./watchmap /usr/src/app/watchmap
COPY ./pyproject.toml /usr/src/app/

RUN poetry build

FROM python:3.11-slim-buster

COPY --from=builder /usr/src/app/dist/watchmap* /usr/src/app/

RUN pip install /usr/src/app/watchmap*.tar.gz && rm /usr/src/app/watchmap*.tar.gz

CMD ["watchmap"]