#! /software/lsstsw/stack_20200515/python/miniconda3-4.7.12/envs/lsst-scipipe/bin/python
import configargparse
from datetime import datetime, timedelta, timezone
import time
import sqlite3
import sys
import os
from webpage import db_to_html
from jinja2 import Template
import logging
from styles import css

# Configure logging
log = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)
try:
    log.setLevel(os.environ['LOG_LEVEL'].upper())
except:
    log.setLevel('DEBUG')

if len(sys.argv) < 2:
    print("mainpage.py output indir1 indir2...")
    print("output is the output directory webpage")
    print("indir are output dirs written to by observing_monitor.py")
    print("If indirs do not begin with a '/' they are assumed to be appended on output")
    sys.exit()
now = datetime.utcnow()
nowstr= now.strftime('%Y-%m-%dT%H:%M:%S')
firstnite=(now-timedelta(days=30)).strftime('%Y-%m-%d')

outdir=sys.argv[1]
outfile = f'{outdir}/index.html'

streams = []
for indir in sys.argv[2:]:
    try:
        if indir[0] != '/':
            indir = f'{outdir}/{indir}'
        db = f'{indir}/observing_monitor.sqlite3'
        streams.append({
            'name': indir.split('/')[-1],
            'link': indir.split('/')[-1],
            'html': db_to_html(db, f'select * from FILE_COUNT where Nite_Obs >= "{firstnite}" order by Nite_Obs DESC'),
        })
        if os.path.exists(f'{indir}/index_gen3.html'):
            streams.append({
                'name': f'''{indir.split('/')[-1]} Gen 3''',
                'link': f'''{indir.split('/')[-1]}/index_gen3.html''',
                'data_table': db_to_html(db, f'select * from FILE_COUNT_GEN3 where Nite_Obs >= "{firstnite}" order by Nite_Obs DESC'),
            })
    except Exception as e:
        log.error(f'{str(e)}')
try:
    # Render table template after populating with query results
    with open(os.path.join(os.path.dirname(__file__), "mainpage.tpl.html")) as f:
        templateText = f.read()
    template = Template(templateText)
    html = template.render(
        css=css,
        nowstr=nowstr,
        streams=streams,
    )
    # log.debug(f'{html}')
except Exception as e:
    log.error(f'{str(e)}')
    html = f'{str(e)}'

with open(outfile, 'w') as outf:
    outf.write(html)
