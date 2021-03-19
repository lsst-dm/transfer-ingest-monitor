#! /software/lsstsw/stack_20200515/python/miniconda3-4.7.12/envs/lsst-scipipe/bin/python
import configargparse
from datetime import datetime, timedelta, timezone
import time
import sqlite3
import sys
import os
from webpage import db_to_html

if len(sys.argv) < 2:
  print("mainpage.py output indir1 indir2...")
  print("output is the output directory webpage")
  print("indir are output dirs written to by observing_monitor.py")
  print("If indirs do not begin with a '/' they are assumed to be appended on output")
  sys.exit()
now = datetime.utcnow()
nowstr= now.strftime('%Y-%m-%dT%H:%M:%S')
firstnite=(now-timedelta(days=2)).strftime('%Y-%m-%d')

outdir=sys.argv[1]
outhtml=open(outdir+'/index.html','w')
outhtml.write('<html>\n<head>\n<style>\n')
outhtml.write('table, th, td {\nborder-collapse: collapse;\nfont-size: 20pt;\n }\n')
outhtml.write('p {font-size: 20pt;\n }\n')
outhtml.write('</style>\n')
outhtml.write('</head>\n<body>\n')
outhtml.write('<p>Last updated: '+nowstr+'</p>\n')
outhtml.write('<h1>NCSA/LSST Transfer/Ingestion Summary Page</h1>\n')

for indir in sys.argv[2:]:
   if indir[0] != '/':
      indir = outdir+'/'+indir
   stream = indir.split('/')[-1]
   db = indir+'/observing_monitor.sqlite3'
   outhtml.write('\n<h2><a href="'+stream+'">'+stream+'</a></h2>\n')
   outhtml.write(db_to_html(db, 'select * from FILE_COUNT where Nite_Obs >= "'+firstnite+'" order by Nite_Obs DESC'))

   if os.path.exists(indir+"/index_gen3.html"):
       outhtml.write('\n<h2><a href="'+stream+'/index_gen3.html">'+stream+' Gen 3</a></h2>\n')
       outhtml.write(db_to_html(db, 'select * from FILE_COUNT_GEN3 where Nite_Obs >= "'+firstnite+'" order by Nite_Obs DESC'))
   
outhtml.write('</body>\n</html>')
outhtml.close()

