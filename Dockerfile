FROM keppel.eu-de-1.cloud.sap/ccloud-dockerhub-mirror/library/python:3.11-alpine as base
FROM base as builder

RUN apk update \
    && apk upgrade \
    && apk add --update --no-cache --virtual build-deps gcc python3-dev musl-dev libc-dev linux-headers libxslt-dev libxml2-dev \
    && apk add libffi-dev openssl-dev 
RUN python -m pip install --upgrade pip

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip3 install --prefix="/install" -r /requirements.txt

FROM base

COPY --from=builder /install /usr/local

COPY src /app
WORKDIR /app

LABEL source_repository="https://github.com/sapcc/ironic_exporter"
LABEL maintainer="Bernd Kuespert <bernd.kuespert@sap.com>"

CMD ["python", "main.py"]
