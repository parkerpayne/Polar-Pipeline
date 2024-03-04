FROM python:3.11.3-slim-buster

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y netcat perl make libdbi-perl libwww-perl libc6-dev cpanminus build-essential tabix
RUN cpan install FindBin
RUN cpan Math::CDF
RUN cpan List::MoreUtils

RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

COPY ./vep/.vep /root/.vep
COPY . /usr/src/app

ENTRYPOINT [ "/usr/src/app/entrypoint.sh" ]