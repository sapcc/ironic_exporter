FROM keppel.eu-de-1.cloud.sap/ccloud-dockerhub-mirror/library/python:latest as base
FROM base as builder

RUN export DEBIAN_FRONTEND=noninteractive \
    && apt update \
    && apt upgrade -y \
    && apt full-upgrade -y 

#RUN apt install libffi-dev openssl-dev

RUN python -m pip install --upgrade pip

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip3 install --prefix="/install" -r /requirements.txt

FROM builder

COPY --from=builder /install /usr/local

COPY src /app
WORKDIR /app

LABEL source_repository="https://github.com/sapcc/ironic_exporter"
LABEL maintainer="Bernd Kuespert <bernd.kuespert@sap.com>"

CMD ["python", "main.py"]
