#!/bin/bash -e

if [[ "x$1" == "x" ]]; then
    tag="dev"
else
    tag="$1"
fi

repo="lsstdm/transfer-ingest-monitor"
echo "Building ${repo}:${tag} ..."
docker build -t ${repo}:${tag} .
echo "Pushing ${repo}:${tag} ..."
docker push ${repo}:${tag}