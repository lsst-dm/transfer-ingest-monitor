FROM ubuntu:20.04

ARG SYNCTHING_VERSION=1.14.0

# Don’t create a default folder when starting for the first time. 
# This variable will be ignored anytime after the first run.
ENV STNODEFAULTFOLDER=1

RUN DEBIAN_FRONTEND=noninteractive apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install dirmngr curl ca-certificates gpg gpg-agent -y --no-install-recommends \
  && DEBIAN_FRONTEND=noninteractive apt-get autoremove -y

# get syncthing
WORKDIR /srv
RUN useradd --no-create-home --shell /bin/bash --uid 1000 syncthing 
RUN curl -L -o syncthing.tar.gz "https://github.com/syncthing/syncthing/releases/download/v$SYNCTHING_VERSION/syncthing-linux-amd64-v$SYNCTHING_VERSION.tar.gz" \
  && tar -xzvf syncthing.tar.gz \
  && rm -f syncthing.tar.gz \
  && mv syncthing-linux-amd64-v* syncthing \
  && rm -rf syncthing/etc \
  && rm -rf syncthing/*.pdf \
  && mkdir -p /srv/config \
  && mkdir -p /srv/data

RUN chown -R syncthing:syncthing /srv/syncthing