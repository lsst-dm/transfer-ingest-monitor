#!/bin/bash

docker build -t lsstdm/transfer-ingest-monitor:latest . && \
docker push lsstdm/transfer-ingest-monitor:latest