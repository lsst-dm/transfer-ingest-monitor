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
from styles import html_head

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
    print("render_summary_page.py output indir1 indir2...")
    print("output is the output directory webpage")
    print("indir are output dirs written to by observing_monitor.py")
    print("If indirs do not begin with a '/' they are assumed to be appended on output")
    sys.exit()
# Number of days to include on the summary page
try:
    num_days = int(os.environ['SUMMARY_NUM_DAYS'])
except:
    num_days = 30
now = datetime.utcnow()
nowstr= now.strftime('%Y-%m-%dT%H:%M:%S')
firstnite=(now-timedelta(days=num_days)).strftime('%Y-%m-%d')

outdir=sys.argv[1]
outfile = f'{outdir}/index.html'

streams3 = []
# Render Gen3
for indir in sys.argv[2:]:
    try:
        if indir[0] != '/':
            indir = f'{outdir}/{indir}'
        db = f'{indir}/observing_monitor.sqlite3'
        log.debug(f'DB path: {db}')
        if os.path.exists(f'{indir}/index.html'):
            streams3.append({
                'name': f'''{indir.split('/')[-1]} <span style="font-size:smaller; font-variant:all-small-caps">(Gen 3)</span>''',
                'link': f'''{indir.split('/')[-1]}''',
                'data_table': db_to_html(db, f'''SELECT * FROM FILE_COUNT_GEN3 WHERE Nite_Obs >= "{firstnite}" AND N_Files > 0 ORDER BY Nite_Obs DESC''', linkify=True, prefix=f'''{indir.split('/')[-1]}/''', table_sortable=False),
                'gen': 3,
            })
            log.debug(f'    gen3 added: {streams3[-1]}')
    except Exception as e:
        log.error(f'{str(e)}')
# Render Gen2
streams2 = []
for indir in sys.argv[2:]:
    try:
        if indir[0] != '/':
            indir = f'{outdir}/{indir}'
        db = f'{indir}/observing_monitor.sqlite3'
        log.debug(f'DB path: {db}')
        if os.path.exists(f'{indir}/index_gen2.html'):
            streams2.append({
                'name': f'''{indir.split('/')[-1]} <span style="font-size:smaller; font-variant:all-small-caps">(Gen 2)</span>''',
                'link': f'''{indir.split('/')[-1]}/index_gen2.html''',
                'data_table': db_to_html(db, f'''SELECT * FROM FILE_COUNT_GEN2 WHERE Nite_Obs >= "{firstnite}" AND N_Files > 0 ORDER BY Nite_Obs DESC''', linkify=True, prefix=f'''{indir.split('/')[-1]}/''', modifier='_gen2', table_sortable=False),
                'gen': 2,
            })
            log.debug(f'    gen2 added: {streams2[-1]}')
    except Exception as e:
        log.error(f'{str(e)}')
try:
    # Render table template after populating with query results
    with open(os.path.join(os.path.dirname(__file__), "templates/summary.tpl.html")) as f:
        templateText = f.read()
    template = Template(templateText)
    html = template.render(
        html_head=html_head,
        nowstr=nowstr,
        streams2=streams2,
        streams3=streams3,
        num_days=num_days,
    )
    # log.debug(f'{html}')
except Exception as e:
    log.error(f'{str(e)}')
    html = f'{str(e)}'

with open(outfile, 'w') as outf:
    outf.write(html)
