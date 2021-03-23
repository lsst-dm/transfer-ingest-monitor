Syncthing deployment
=============================

Initialization
------------------------------

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

Data synchronization
------------------------------

To synchronize data between the Syncthing instances, their configurations must be modified to provide each with the Device ID of the other and with the shared folder information.

Read about the config spec at https://docs.syncthing.net/users/config.html#config-file-format.

For example, adding the following to the Syncthing instance `config.xml` on the public-facing deployment configures Syncthing to connect to the other instance (named `transfer-ingest-monitor-source`) and sync the `webfiles` folder share in `receiveonly` mode.

```
    ...
    <device id="VJ6RLU3-...-JKYVPQ7" name="transfer-ingest-monitor-source" compression="metadata" introducer="false" skipIntroductionRemovals="false" introducedBy="">
        <address>dynamic</address>
        <paused>false</paused>
        <autoAcceptFolders>true</autoAcceptFolders>
        <maxSendKbps>0</maxSendKbps>
        <maxRecvKbps>0</maxRecvKbps>
        <maxRequestKiB>0</maxRequestKiB>
        <untrusted>false</untrusted>
        <remoteGUIPort>0</remoteGUIPort>
    </device>
    <folder id="webfiles" label="webfiles" path="/srv/data" type="receiveonly" rescanIntervalS="3600" fsWatcherEnabled="true" fsWatcherDelayS="10" ignorePerms="false" autoNormalize="true">
        <filesystemType>basic</filesystemType>
        <device id="VJ6RLU3-...-JKYVPQ7" introducedBy="">
            <encryptionPassword></encryptionPassword>
        </device>
        <device id="WUURFXM-...-E56JMQB" introducedBy="">
            <encryptionPassword></encryptionPassword>
        </device>
    </folder>
    ...
```

Conversely, on the Integration cluster Syncthing deployment, the same folder is shared in `sendonly` mode.