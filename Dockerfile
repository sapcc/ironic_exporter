FROM python:3.12-alpine as base
FROM base as builder

RUN apk add --update --no-cache --virtual build-deps gcc python3-dev musl-dev libc-dev linux-headers libxslt-dev libxml2-dev \
&& apk add libffi-dev openssl-dev 
RUN python -m pip install --upgrade pip

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip3 install --prefix="/install" -r /requirements.txt

FROM base
LABEL source_repository="https://github.com/sapcc/ironic_exporter"
COPY --from=builder /install /usr/local
COPY src /app
WORKDIR /app

CMD ["python", "main.py"]
