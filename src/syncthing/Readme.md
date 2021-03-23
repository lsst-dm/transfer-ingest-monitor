Syncthing deployment
=============================

Generate the Syncthing instance configuration file and identity certificates by running the Docker container locally (create a folder `config` to capture the files):

```
$ docker run -it --rm --name syncthing \
    -v "$(pwd)/config":/srv/config \
    -u syncthing \
    lsstdm/transfer-ingest-monitor-syncthing:latest \
    bash

syncthing@bd919f7d54a1:/srv$ /srv/syncthing/syncthing -home=/srv/config
```

This will generate the `config.xml` and `cert.pem` and `key.pem` files you will need to upload to the persistent storage of the deployed Syncthing app.

Copy the files to the deployed volume like so (replacing `transfer-ingest-monitor-syncthing-74c8fd4bb8-jhnkf` with your pod name):

```
kubectl cp config/config.xml transfer-ingest-monitor-syncthing-74c8fd4bb8-jhnkf:/srv/config/config.xml
kubectl cp config/cert.pem transfer-ingest-monitor-syncthing-74c8fd4bb8-jhnkf:/srv/config/cert.pem
kubectl cp config/key.pem transfer-ingest-monitor-syncthing-74c8fd4bb8-jhnkf:/srv/config/key.pem
```

Deleting the pod should trigger a new one to replace it, which will load the desired config.