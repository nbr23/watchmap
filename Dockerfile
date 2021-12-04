FROM python:3.10-slim-buster

WORKDIR /usr/src/app

COPY ./requirements.txt /usr/src/app/requirements.txt

RUN pip3 install --no-cache-dir -r /usr/src/app/requirements.txt

COPY ./watchmap.py /usr/src/app/
RUN ln -s /usr/src/app/watchmap.py /usr/bin/watchmap

CMD ["watchmap"]