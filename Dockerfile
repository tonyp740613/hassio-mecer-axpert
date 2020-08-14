ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

RUN apk add --no-cache python3 && \
    python3 -m ensurepip --upgrade && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools crcmod paho-mqtt && \
    rm -r /root/.cache

COPY monitor.py /
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
