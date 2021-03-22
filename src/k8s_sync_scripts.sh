#!/bin/bash

set -e

scriptPath="$(readlink -f "$0")"
scriptDir="$(dirname "${scriptPath}")"
cd "${scriptDir}" || exit 1

NAMESPACE="$1"
if [[ "X${NAMESPACE}" == "X" ]]; then
  NAMESPACE="lsst-dm"
fi

DEPLOYMENT_NAME="transfer-ingest-monitor"
SOURCE_DIR="transfer-ingest-monitor"
TARGET_DIR="/home/worker/transfer-ingest-monitor"

POD_ID="$(kubectl get pod -n "${NAMESPACE}" --selector=app="${DEPLOYMENT_NAME}" -o jsonpath='{.items[0].metadata.name}')"
echo "Updating source code in ${POD_ID}..."
# export TIMESTAMP="$(date | tr -d '\n')"
TIMESTAMP="$(date | shasum | cut -f1 -d ' ')"
echo "${TIMESTAMP}" > "${SOURCE_DIR}/.codesync"
STRIP_NUM="$(echo "${SOURCE_DIR}" | tr '/' ' ' | wc -w)"
# kubectl exec -i -n "${NAMESPACE}" --container="${DEPLOYMENT_NAME}" "${POD_ID}" -- id
# kubectl exec -i -n "${NAMESPACE}" --container="${DEPLOYMENT_NAME}" "${POD_ID}" -- ls -l "${TARGET_DIR}"
tar cf - "${SOURCE_DIR}" | \
    kubectl exec -i -n "${NAMESPACE}" --container="${DEPLOYMENT_NAME}" "${POD_ID}" -- \
    tar --overwrite -xf - --strip-components="${STRIP_NUM}" -C "${TARGET_DIR}"

LASTSYNC="$(kubectl exec -it -n "${NAMESPACE}" --container="${DEPLOYMENT_NAME}" "${POD_ID}" -- cat "${TARGET_DIR}/.codesync" | tr -d '\n' | tr -d '\r')"
# LASTSYNC="$(echo "${LASTSYNC}" | tr -d '\n' | tr -d '\r')"
if [[ "${LASTSYNC}" == "${TIMESTAMP}" ]]; then
  echo "Sync successful."
  exit 0
else
  echo "Sync failed."
  exit 1
fi
