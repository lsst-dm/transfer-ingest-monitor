#! /software/lsstsw/stack_20200515/python/miniconda3-4.7.12/envs/lsst-scipipe/bin/python
import sqlite3, os, sys

if len(sys.argv) != 2:
   print("photodiode_copy.py DATE")
   print("Where DATE is the earliest date to look for files in YYYY-MM-DD format.")
   sys.exit()

DB ="/lsstdata/offline/web_data/processing_monitor/LSSTCam-bot/observing_monitor.sqlite3"
query='select Transfer_Path from TRANSFER_LIST where Transfer_Path like "%%Photo%txt" and Nite_Trans > "'+sys.argv[1]+'" order by transfer_path'
outdir='photodiodes'
outdir='/lsstdata/offline/instrument/LSSTCam-bot/photodiode_data'
storage='/lsstdata/offline/instrument/LSSTCam-bot/storage/'
clobber = False

if not os.path.exists(outdir):
  os.mkdir(outdir)

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute(query)
rows=c.fetchall()
conn.close()

for path in [row[0] for row in rows]:
   outname=path.split('/')[-1]
   if outname == "Photodiode_Readings.txt":
      dirname=path.split('/')[-2]
      outname = "Photodiode_Readings_"+dirname.split('MC_C_')[1]+".txt"
#   print(path+' '+outdir+'/'+outname)
   outpath = outdir+'/'+outname
   if os.path.exists(outpath):
      if clobber:
         os.remove(outpath)
         os.symlink(storage+'/'+path,outpath)

   else:
     os.symlink(storage+'/'+path,outpath)
