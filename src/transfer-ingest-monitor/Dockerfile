FROM ubuntu:20.04
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*
ARG UID=1000
RUN echo "Building image with \"worker\" user ID: ${UID}"
RUN useradd --create-home --shell /bin/bash worker --uid ${UID}
USER worker
RUN mkdir /home/worker/app
WORKDIR /home/worker/app
COPY --chown=worker:worker ./src/requirements.txt requirements.txt
RUN pip3 install --user -r requirements.txt
COPY --chown=worker:worker ./src/ ./
