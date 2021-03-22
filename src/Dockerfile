FROM ubuntu:20.04
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*
ARG UID=1000
RUN echo "Building image with \"worker\" user ID: ${UID}"
RUN useradd --create-home --shell /bin/bash worker --uid ${UID}
USER worker
WORKDIR /home/worker/transfer-ingest-monitor
COPY --chown=worker:worker ./transfer-ingest-monitor/requirements.txt /home/worker/transfer-ingest-monitor/requirements.txt
RUN pip3 install --user -r requirements.txt
COPY --chown=worker:worker ./transfer-ingest-monitor/ /home/worker/transfer-ingest-monitor/
