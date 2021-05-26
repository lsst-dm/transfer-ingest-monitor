import sqlite3
import os
from jinja2 import Template

import logging

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

def db_to_html(db, query, linkify=False, modifier='', prefix=''):
    html = ''
    try:
        # Query database to get record table
        if isinstance(query,str):
            query=[query]
        conn = sqlite3.connect(db)
        c = conn.cursor()
        # query0 = query[0].replace('\n', ' ')
        # log.debug(f'''query: {query[0]}''')
        c.execute(query[0])
        
        # Extract the column labels
        columns= [description[0] for description in c.description]

        num_files_idx = -1
        colIdx = 0
        for col in columns:
            if col == 'N_Files':
                num_files_idx = colIdx
            colIdx += 1
        # log.debug(f'columns: {columns}')
        # Store records in array
        rows=c.fetchall()
        for num in range(1,len(query)):
            c.execute(query[num])
            rows.extend(c.fetchall())
            
        # log.debug(f'rows: {rows}')
        records = []
        for row in rows:
            if len(row) > 1:
                vals = [r for r in row[1:]]
                row_linkify = linkify
                if num_files_idx >= 0 and linkify and vals[num_files_idx-1] < 1:
                    row_linkify = False
                records.append({
                    'link_url': f'{prefix}{row[0]}{modifier}.html',
                    'link_text': f'{row[0]}',
                    'vals': vals,
                    'linkify': row_linkify,
                })
        try:
            if not records:
                return html
            # Render table template after populating with query results
            with open(os.path.join(os.path.dirname(__file__), "table.tpl.html")) as f:
                templateText = f.read()
            template = Template(templateText)
            html = template.render(
                headers=columns,
                records=records,
                linkify=linkify
            )
            # log.debug(f'{html}')
        except Exception as e:
            log.error(f'{str(e)}')
    except Exception as e:
        log.error(f'DB: {db}, Error message: {str(e)}')

    return html
