Transfer and Ingest Monitor
======================================

The Transfer and Ingest Monitor (TIM) provides a data transfer and ingest monitoring service for the Vera C. Rubin Observatory Legacy Survey of Space and Time (LSST).

Secrets
----------------------

Secrets are manually generated. See `secrets.sample` for details.

Endpoint Manager DB
----------------------------
 
The Endpoint Manager DB can be accessed when the `pgpass` Secret is mounted as `$HOME/.pgpass` for the container system user. For example

```
$ psql \
    --host=lsst-pg-prod1.ncsa.illinois.edu \
    --username=svclsstdbdbbbm \
    --dbname=lsstdb1
    
psql (13.2 (Debian 13.2-1.pgdg100+1), server 12.6)
SSL connection (protocol: TLSv1.2, cipher: ECDHE-RSA-AES256-GCM-SHA384, bits: 256, compression: off)
Type "help" for help.

lsstdb1=> select filename,size_bytes from nts_auxtel_files limit 3;
             filename              | size_bytes 
-----------------------------------+------------
 AT_O_20200325_000002--R00S00.fits |   75582720
 AT_O_20200325_000003--R00S00.fits |   75582720
 AT_O_20200325_000001--R00S00.fits |   75582720
(3 rows)

```