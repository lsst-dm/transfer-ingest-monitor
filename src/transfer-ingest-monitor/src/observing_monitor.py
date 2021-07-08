#! /software/lsstsw/stack_20200515/python/miniconda3-4.7.12/envs/lsst-scipipe/bin/python
import configargparse
from datetime import datetime, timedelta, timezone
import time
import sqlite3
import sys
import os
import glob
import numpy as np
import pandas as pd
import re
import sqlalchemy
import statistics
import traceback
import psycopg2
from webpage import db_to_html
from jinja2 import Template
from styles import html_head
import logging
from pathlib import Path
import re
import yaml

from astropy.time import Time, TimeDelta
from lsst_efd_client import EfdClient
import asyncio

# Configure logging
log = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)
try:
    log.setLevel(os.environ['LOG_LEVEL'].upper())
except:
    log.setLevel('WARNING')

def timestamp_to_string(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%S")

def nite_from_timestamp(timestamp):
    return (datetime.utcfromtimestamp(timestamp)-timedelta(hours=12)).strftime('%Y-%m-%d')

def nite_from_timestring(timestr):
    return (datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%S.%f')-timedelta(hours=12)).strftime('%Y-%m-%d')

def rec_listdir(dir):
    output = []
    filelist = os.listdir(dir)
    for file in filelist:
        if os.path.isdir(os.path.join(dir, file)):
           for file2 in os.listdir(os.path.join(dir, file)):
               if file2[0] != '.':
                  output.append(os.path.join(file, file2))
        else:
           if file[0] != '.':
              output.append(file)
    return sorted(output)

def get_config():
    """Parse command line args, config file, environment variables to get configuration.
    Returns
    -------
    config: `dict`
        Configuration values for program.
    """
    parser = configargparse.ArgParser(config_file_parser_class=configargparse.YAMLConfigFileParser,
                                      auto_env_var_prefix="RSYMON_")
    # parser.add('--input_dir', action='store', type=str, required=True,
    #            help='Path to input directory at NCSA. Must include storage and gen2repo subdirectories')
    parser.add('--first_day', action='store', type=str, required=False,
               help='Date in YYYYMMDD format for first. Must be before last day. Will override num_days')
    # parser.add('--gen', action='store', type=int, required=False, default=2, choices=[2,3],
    #            help='Generation butler (2 or 3) supported.')
    parser.add('--last_day', action='store', type=str, required=False,
               help='Date in YYYYMMDD format for last day if not today.')
    parser.add('--output_dir', action='store', type=str, required=True,
               help='Path to output directory where DB and webpage will live')
    parser.add('--search_links', action='store_true',
               help='Search repo for all links (for repos with nonstandard db format).')
    parser.add('--num_days', action='store', type=int, required=False,
               help='Number of days before the last date.')
    parser.add('--source_config', action='store', type=str, required=True,
               help='Path to data source config file')
    parser.add('--source_name', action='store', type=str, required=True,
               help='Name of data source in data source config file to monitor')
    config = vars(parser.parse_args())
    return config

class TransferIngestMonitor:
    def __init__(self, config):
        # Load the data source config
        try:
            with open(config['source_config'], 'r') as conf_file:
                data_sources = yaml.safe_load(conf_file)
                # data_sources = yaml.safe_load(dev_config)
                self.data_source = [src for src in data_sources if src['name'] == config['source_name']][0]
        except Exception as e:
            log.error(str(e))
            log.error(f"""Could not determine database for source named "{config['source_name']}". Exiting""")
            sys.exit(1)

        # Set the data source name
        self.name = config['source_name']
        
        # Store the current time
        self.now = datetime.utcnow()
        self.nowstr = self.now.strftime('%Y-%m-%dT%H:%M:%S')
        last_day = config['last_day']
        first_day = config['first_day']
        num_days = config['num_days']
        # Last day
        if last_day:
            self.last_day = datetime(int(last_day[0:4]), int(last_day[4:6]), int(last_day[6:8]), 0, tzinfo=timezone.utc)
        else:
            self.last_day = self.now
        # First day
        if first_day:
            self.first_day = datetime(int(first_day[0:4]), int(first_day[4:6]), int(first_day[6:8]), 0, tzinfo=timezone.utc)
            self.num_days = int((self.last_day.timestamp()-self.first_day.timestamp())/3600/24+1)
        elif num_days:
            self.num_days = num_days
            self.first_day = self.last_day-timedelta(days=self.num_days)
        else:
            self.num_days = 2
            self.first_day = self.last_day-timedelta(days=self.num_days)

        if self.first_day > self.last_day:
            log.error("First day is after last day. Exiting.")
            sys.exit(1)
        
        log.debug(f'{yaml.dump(self, indent=2)}')
        
        self.image_data = []
        
        # Initialize data source file paths
        self.input_dir = Path(self.data_source['data_dir'])
        self.repo_dir  = os.path.join(self.input_dir, 'gen2repo')
        self.storage   = os.path.join(self.input_dir, 'storage')
        self.raw_dir   = os.path.join(self.repo_dir, 'raw')
        self.repo      = os.path.join(self.repo_dir, 'registry.sqlite3')
        for dir in [self.input_dir, self.repo_dir, self.storage, self.raw_dir, self.repo]:
            if not os.path.exists(dir):
                log.error(f"{dir} does not exist. Exiting.")
                sys.exit(1)
        
        # Initialize the output paths
        self.output_dir = Path(config['output_dir'])
        os.makedirs(self.output_dir, exist_ok=True)
        self.html = os.path.join(self.output_dir, 'index.html')
        self.db = os.path.join(self.output_dir, 'observing_monitor.sqlite3')
        if not os.path.exists(self.output_dir):
          log.error(f"You do not have access to {self.output_dir}. Exiting.")
          sys.exit(1)
        
  
        # Initialize the monitor SQLite database
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS FILE_COUNT_GEN3 (
                Nite_Obs TEXT PRIMARY KEY,
                Last_Update TEXT,
                N_Files INTEGER,
                Last_Creation TEXT,
                N_Ingest INTEGER,
                N_Small INTEGER,
                N_Not_Fits,
                N_Error INTEGER,
                Last_Discovery TEXT,
                Last_Ingest TEXT,
                Gen TEXT
            )'''
        )
        c.execute('''
            CREATE TABLE IF NOT EXISTS FILE_COUNT_GEN2 (
                Nite_Obs TEXT PRIMARY KEY,
                Last_Update TEXT,
                N_Files INTEGER,
                Last_Creation TEXT,
                N_Ingest INTEGER,
                N_Small INTEGER,
                N_Not_Fits,
                N_Error INTEGER,
                Last_Discovery TEXT,
                Last_Ingest TEXT,
                Gen TEXT
            )'''
        )
        c.execute('''
            CREATE TABLE IF NOT EXISTS FILE_LIST_GEN3 (
                Filenum INTEGER PRIMARY KEY,
                Nite TEXT,
                Last_Update TEXT,
                Transfer_Path TEXT,
                Status TEXT,
                Creation_Time TEXT,
                Discovery_Time TEXT,
                Ingest_Time TEXT,
                File_Size INT,
                Err_Message TEXT,
                Gen TEXT
            )'''
        )
        c.execute('''
            CREATE TABLE IF NOT EXISTS FILE_LIST_GEN2 (
                Filenum INTEGER PRIMARY KEY,
                Nite TEXT,
                Last_Update TEXT,
                Transfer_Path TEXT,
                Status TEXT,
                Creation_Time TEXT,
                Discovery_Time TEXT,
                Ingest_Time TEXT,
                File_Size INT,
                Err_Message TEXT,
                Gen TEXT
            )'''
        )
        c.execute('''
            CREATE TABLE IF NOT EXISTS IMAGE_DATA (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                EfdHost TEXT NOT NULL DEFAULT '',
                EfdTable TEXT NOT NULL DEFAULT '',
                ImageName TEXT NOT NULL DEFAULT '',
                ImageFileName TEXT NOT NULL DEFAULT '',
                Creation_Time TEXT NOT NULL DEFAULT '0000-00-00T00:00:00',
                InTransfers INT DEFAULT 0,
                Nite TEXT NOT NULL DEFAULT '0000-00-00'
            )'''
        )
        conn.commit()
        conn.close()

    def set_date(self, num):
        self.nite = (self.last_day-timedelta(days=num)).strftime('%Y-%m-%d')
        self.nite_no_hyphen = (self.last_day-timedelta(days=num)).strftime('%Y%m%d')
        self.next_nite = (self.last_day-timedelta(days=num-1)).strftime('%Y-%m-%d')
        self.next_nite_no_hyphen = (self.last_day-timedelta(days=num-1)).strftime('%Y%m%d')
        mintime = datetime(int(self.nite[0:4]), int(self.nite[5:7]), int(self.nite[8:10]), 12, tzinfo=timezone.utc)
        self.mintime = mintime.timestamp()
        self.maxtime = (mintime+timedelta(days=1)).timestamp()
        log.debug(f"**********************************\nCurrent night: {self.nite}\n**********************************\n")

    async def query_efd(self):
        first_nite = Time(f'{self.first_day.strftime("%Y-%m-%d")}T00:00:00', scale='tai')
        last_nite  = Time(f'{self.last_day.strftime("%Y-%m-%d")}T00:00:00', scale='tai')
        self.image_data = []
        try:
            table_name = self.data_source['efd']['table']
            data_source_type = self.data_source['type']
            cl = EfdClient(self.data_source['efd']['host']).influx_client
        except:
            return
        # images array captures all image data obtained from the EFD
        # images = []
        image_template = {
            'efd_host': self.data_source['efd']['host'],
            'table_name': '',
            'data_source_type': '',
            'image_name': '',
            'filename': '',
            'nite': '0000-00-00',
            'creation_timestamp': 0,
            'creation_time': '0000-00-00T00:00:00',
        }
        if data_source_type == 'ccs':
            query = f'''
                SELECT 
                    "imageName",
                    "timestampEndOfReadout"
                FROM "efd"."autogen"."{table_name}"
                WHERE time >= '{first_nite.isot}Z' AND time < '{last_nite.isot}Z'
            '''
            result = await cl.query(query)
            if len(result) > 0:
                for index, row in result.iterrows():
                    try:
                        image = dict(image_template)
                        image['table_name'] = table_name
                        image['data_source_type'] = data_source_type
                        image['image_name'] = row['imageName']
                        image['creation_timestamp'] = row['timestampEndOfReadout']
                        image['creation_time'] = timestamp_to_string(image['creation_timestamp'])
                        image['nite'] = nite_from_timestamp(image['creation_timestamp'])
                        self.image_data.append(image)
                        # log.debug(f'{self.image_data[-1]}')
                    except Exception as e:
                        log.error(f'Error parsing row: {str(e)}')
        elif data_source_type == 'arc':
            query = f'''
                SELECT 
                    "obsid",
                    "raft",
                    "sensor",
                    "private_rcvStamp"
                FROM "efd"."autogen"."{table_name}"
                WHERE time >= '{first_nite.isot}Z' AND time < '{last_nite.isot}Z' AND raft != '' AND sensor != ''
            '''
            result = await cl.query(query)
            if len(result) > 0:
                for index, row in result.iterrows():
                    try:
                        image = dict(image_template)
                        image['table_name'] = table_name
                        image['data_source_type'] = data_source_type
                        image['image_name'] = row['obsid']
                        image['creation_timestamp'] = row['private_rcvStamp']
                        image['creation_time'] = timestamp_to_string(image['creation_timestamp'])
                        image['nite'] = nite_from_timestamp(image['creation_timestamp'])
                        zero_pad_sensor = '0' if len(row['sensor']) == 1 else ''
                        zero_pad_raft = '0' if len(row['raft']) == 1 else ''
                        image['filename'] = f'''{row['obsid']}-R{zero_pad_raft}{row['raft']}S{zero_pad_sensor}{row['sensor']}.fits'''
                        self.image_data.append(image)
                        # log.debug(f'{self.image_data[-1]}')
                    except Exception as e:
                        log.error(f'Error parsing row: {str(e)}')
        else:
            log.error(f"""Unsupported data source type "{data_source_type}". Exiting""")
            sys.exit(1)
        
        # Update IMAGE_DATA table
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        for image in self.image_data:
            c.execute(f'''
                DELETE FROM IMAGE_DATA WHERE
                    EfdHost = '{image['efd_host']}' AND
                    EfdTable = '{self.data_source['efd']['table']}' AND
                    ImageName = '{image['image_name']}' AND
                    ImageFileName = '{image['filename']}' AND
                    Creation_Time = '{image['creation_time']}' AND
                    Nite = '{image['nite']}'
            ''')
            c.execute(f'''
                INSERT INTO IMAGE_DATA (
                    EfdHost,
                    EfdTable,
                    ImageName,
                    ImageFileName,
                    Creation_Time,
                    Nite
                ) VALUES(
                   '{image['efd_host']}',
                   '{image['table_name']}',
                   '{image['image_name']}',
                   '{image['filename']}',
                   '{image['creation_time']}',
                   '{image['nite']}'
                )
            ''')
        conn.commit()
        conn.close()

    def query_consolidated_db(self):

        def parse_date_from_path(indate):
            if len(indate) == 8:
                if indate.isdigit():
                    return indate[:4]+'-'+indate[4:6]+'-'+indate[6:8]
            if len(indate) == 10:
                if indate[:4].isdigit() & indate[5:7].isdigit() & indate[8:10].isdigit():
                    return indate[:4]+'-'+indate[5:7]+'-'+indate[8:10]
            return ''

        # For efficiency, query consolidated db for all files with names that include the dates in the current search range.
        daystr = (self.first_day).strftime('%Y%m%d')
        filename_condition = f"""filename LIKE '%%{daystr}%%.fits'"""
        for day in range(1,self.num_days):
            daystr = (self.first_day+timedelta(days=day)).strftime('%Y%m%d')
            filename_condition += f""" OR 
                        filename LIKE '%%{daystr}%%.fits'"""
        
        self.ids = {}
        self.paths = {}
        self.filenames = {}
        self.nites = {}
        self.statuss = {}
        self.ctimes = {}
        self.ttimes = {}
        self.itimes = {}
        self.durations = {}
        self.filesizes = {}
        self.err_messages = {}
        
        for gen in [2, 3]:
            log.debug(f'''\n**********************************\nquery_consolidated_db: gen{gen}\n**********************************\n''')
            files_table = self.data_source['consolidated_db'][f'gen{gen}']['files_table']
            for file_events_table in self.data_source['consolidated_db'][f'gen{gen}']['file_events_tables']:
            # file_events_tables = ','.join(self.data_source['consolidated_db'][f'gen{gen}']['file_events_tables'])
                query = f'''
                set TIMEZONE='UTC'; 
                WITH 
                    ne AS (
                        SELECT 
                            id, 
                            filename,
                            relpath||'/'||filename as path, 
                            status, 
                            added_on, 
                            start_time, 
                            err_message,
                            duration,
                            size_bytes
                        FROM 
                            {files_table}, 
                            {file_events_table}
                        WHERE 
                            files_id = id 
                            AND (
                                {filename_condition}
                            )
                    ),  
                    max AS (
                        SELECT 
                            id as mid, 
                            max(start_time) as mtime 
                        FROM ne 
                        GROUP BY id
                    ) 
                SELECT 
                    id, 
                    filename,
                    path, 
                    status, 
                    CAST(CAST(added_on as timestamp) as varchar(25)) as ttime, 
                    CAST(CAST(start_time as timestamp) as varchar(25)) as itime, 
                    err_message,
                    duration,
                    size_bytes
                FROM 
                    ne, 
                    max 
                WHERE 
                    id = mid 
                    AND 
                    mtime = start_time
                '''
                db = {
                    'user': os.environ['PG_USERNAME'],
                    'host': os.environ['PG_HOST'],
                    'port': os.environ['PG_PORT'],
                    'db': os.environ['PG_DATABASE'],
                }
                engine = sqlalchemy.create_engine(f'''postgresql://{db['user']}@{db['host']}:{db['port']}/{db['db']}''')
                df = pd.read_sql(query, engine)
                log.debug(f'query: {query}')
                log.debug(f'Results:\n{df}')
                
                # Basic metadata
                self.ids[gen] = np.array(df['id'], dtype=int)
                self.paths[gen] = np.array(df['path'])
                self.filenames[gen] = np.array(df['filename'])
                
                # nites captures a simplified timestamp for the day on which the DBB Endpoint Manager DB discovered the file
                self.nites[gen] = np.array(len(df)*['0000-00-00'])
                
                # ctimes is a placeholder for the image creation time
                self.ctimes[gen] = np.array(len(df)*['0000-00-00T00:00:00'])
                
                # Status of ingest attempt
                self.statuss[gen] = np.array(df['status'])

                # ttime is the time the file was discovered by the DBB Endpoint Manager DB
                self.ttimes[gen] = np.array(df['ttime'])

                # itime is the start time of the most recent event. Usually, there are three events for each file:
                # (1) file was added to the "waiting list", status UNTRIED;
                # (2) file was selected for ingestion, status: PENDING;
                # (3) ingest attempt was made, status can be either SUCCESS, FAILURE, or UNKNOWN. Each event is timed individually.
                self.itimes[gen] = np.array(df['itime'])

                # Duration is how long the ingestion took (usually negligible)
                self.durations[gen] = np.array(df['duration'])

                # File size
                self.filesizes[gen] = np.array(df['size_bytes'])
                # Error message associated with FAILURE events
                self.err_messages[gen] = np.array(df['err_message'])
                self.err_messages[gen][self.err_messages[gen] == None] = ''
                
                # Process each record
                for num in range(len(df)):
                    full_path = os.path.join(self.storage, self.paths[gen][num])
                    self.ttimes[gen][num] = self.ttimes[gen][num].replace(' ', 'T')
                    self.itimes[gen][num] = self.itimes[gen][num].replace(' ', 'T')
                    if not os.path.exists(full_path):
                        log.warning(f'''File path not found: "{full_path}"''')
                    # Determine the date of the transfer from the file path. If not
                    self.nites[gen][num] = parse_date_from_path(self.paths[gen][num].split('/')[0])
                    if not self.nites[gen][num]:
                        self.nites[gen][num] = nite_from_timestring(self.ttimes[gen][num])

    def update_monitor_db(self):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        # log.debug(f'IDs: {self.ids}')
        # log.debug(f'''Image search: "{[image['filename'] for image in self.image_data]}"''')
        images_recorded = {
            2: 0,
            3: 0,
        }
        images_not_in_transfers = []
        for gen in [2, 3]:
            log.debug(self.nites[gen])
            log.debug(self.paths[gen])
            log.debug(self.filenames[gen])
        for image in self.image_data:
            # log.debug(yaml.dump(image, indent=2))
            log.debug(f'''{image['creation_time'], image['filename']}''')
            data_source_type = image['data_source_type']
            # Cross-match the image data from the EFD with the transfer database to provide the approximate image data creation time
            for gen in [2, 3]:
                if data_source_type == 'ccs':
                    try:
                        search = [idx for idx, path in enumerate(self.paths[gen]) if image['image_name'] == path.split('/')[1] ]
                        log.debug(search)
                        # Creation times are approximate. Each file listed by the transfer database matching
                        for idx in search:
                            self.ctimes[gen][idx] = image['creation_time']
                    except Exception as e:
                        log.error(f'''Error cross-matching CCS image names with transfer paths:\n"{yaml.dump(image, indent=2)}''')
                elif data_source_type == 'arc':
                    # Cross-match the consolidated db records with the EFD image data records
                    search = [idx for idx, filename in enumerate(self.filenames[gen]) if image['filename'] == filename ]
                    log.debug(search)
                    if search:
                        query = f'''
                            UPDATE IMAGE_DATA SET InTransfers = 1 WHERE ImageFileName = '{image['filename']}'
                            '''
                        c.execute(query)
                        conn.commit()
                        self.ctimes[gen][search[0]] = image['creation_time']
                    elif image['filename'] not in images_not_in_transfers:
                        images_not_in_transfers.append(image['filename'])
                        log.warning(f'''Image file not found in consolidated db: "{image['filename']}"''')
                    if len(search) > 1:
                        log.warning(f'''(gen{gen}) More than one filename matches the image "{image['filename']}":\n{search}''')
                else:
                    log.error(f"""Unsupported data source type "{data_source_type}". Exiting""")
                    sys.exit(1)
        # Insert or update the file information in the monitor db
        for gen in [2, 3]:
            for idx in range(len(self.filenames[gen])):
                query = f'''
                    INSERT OR REPLACE INTO FILE_LIST_GEN{gen} (
                        Filenum, 
                        Nite, 
                        Last_Update, 
                        Transfer_Path, 
                        Status, 
                        Creation_Time, 
                        Discovery_Time, 
                        Ingest_Time, 
                        File_Size, 
                        Err_Message,
                        Gen
                    ) VALUES(
                        :ids,
                        :nites,
                        :now,
                        :paths,
                        :statuss,
                        :ctimes,
                        :ttimes,
                        :itimes,
                        :filesizes, 
                        :errmsg,
                        :gen
                    )
                    '''
                c.execute(query, {
                    'ids': str(self.ids[gen][idx]),
                    'nites': self.nites[gen][idx],
                    'now': self.nowstr,
                    'paths': self.paths[gen][idx],
                    'statuss': self.statuss[gen][idx],
                    'ctimes': self.ctimes[gen][idx],
                    'ttimes': self.ttimes[gen][idx],
                    'itimes': self.itimes[gen][idx],
                    'filesizes': str(self.filesizes[gen][idx]),
                    'errmsg': self.err_messages[gen][idx],
                    'gen': f'gen{gen}',
                })
                images_recorded[gen] += 1
                conn.commit()
            if len(self.ids[gen]) > 0:
                log.info(f"Inserted or replaced {images_recorded[gen]} into FILE_LIST_GEN2 and FILE_LIST_GEN3.")
        conn.close()

    def compile_info_per_night(self):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        sizemin = '10000'
        for gen in [2, 3]:
            log.debug(f'''\n**********************************\ncompile_info_per_night: gen{gen}\n**********************************\n''')
            c.execute(f'''
                SELECT 
                    count(Transfer_Path),
                    max(Creation_Time),
                    sum(Status == "SUCCESS"),
                    max(Discovery_Time),
                    max(Ingest_Time),
                    sum(substr(Transfer_Path,-5) != ".fits"),
                    sum(
                        (substr(Transfer_Path,-5) == ".fits")*(File_Size < {sizemin})
                    ),
                    sum(
                        (substr(Transfer_Path,-5) == ".fits")*(File_Size > {sizemin})*(Status != "SUCCESS")
                    ) 
                FROM FILE_LIST_GEN{gen} t 
                WHERE Nite = "{self.nite}"
                GROUP BY Nite
            ''')
            rows = c.fetchall()
            log.debug(rows)
            if len(rows) > 0:
                [self.ntransfer, self.maxctime, self.ningest, self.maxttime, self.maxitime, self.nnotfits, self.nsmall, self.nerror] = rows[0]
            else:
                [self.ntransfer, self.maxctime, self.ningest, self.maxttime, self.maxitime, self.nnotfits, self.nsmall, self.nerror] = [0, '0000-00-00T00:00:00', 0, '0000-00-00T00:00:00', '0000-00-00T00:00:00', 0, 0, 0]
            update_sql = f'''
                INSERT OR REPLACE INTO FILE_COUNT_GEN{gen} (
                    Nite_Obs,
                    Last_Update,
                    N_Files,
                    Last_Creation,
                    N_Ingest,
                    N_Small,
                    N_Not_Fits,
                    N_Error,
                    Last_Discovery,
                    Last_Ingest,
                    Gen
                ) VALUES(
                    '{self.nite}',
                    '{self.nowstr}',
                    {str(self.ntransfer)},
                    '{self.maxctime}',
                    {str(self.ningest)},
                    {str(self.nsmall)},
                    {str(self.nnotfits)},
                    {str(self.nerror)},
                    '{self.maxttime}',
                    '{self.maxitime}',
                    'gen{gen}'
                    )
            '''
            log.debug(update_sql)
            c.execute(update_sql)
            conn.commit()
        conn.close()

    def update_nite_html(self):
        for gen in [2, 3]:
            log.debug(f'''\n**********************************\nupdate_nite_html: gen{gen}\n**********************************\n''')
            if gen == 3:
                outfilename = f'{self.output_dir}/{self.nite}.html'
            else:
                outfilename = f'{self.output_dir}/{self.nite}_gen2.html'
            data = db_to_html(self.db, [f'''
                SELECT 
                    Transfer_Path, 
                    Status, 
                    File_Size,
                    Creation_Time,
                    Discovery_Time,
                    Ingest_Time,
                    printf("%.1f",(julianday(Discovery_Time)-julianday(Creation_Time))*24*3600.) as Delta_Time_1,
                    printf("%.1f",(julianday(Ingest_Time)-julianday(Discovery_Time))*24*3600.) as Delta_Time_2,
                    Err_Message 
                FROM FILE_LIST_GEN{gen}
                WHERE Nite = "{self.nite}"
                ORDER BY Creation_Time
            '''
            ])
            
            missing_images = db_to_html(self.db, f'''
                SELECT 
                    ImageName,
                    ImageFileName,
                    Creation_Time,
                    InTransfers,
                    Nite
                FROM IMAGE_DATA
                WHERE Nite = "{self.nite}" AND InTransfers = 0
            '''
            )
            log.debug(f'\n*************************************\nMissing files:\n{missing_images}')
        # else:
        #     data = db_to_html(self.db, [
        #         f'''
        #         SELECT 
        #             Transfer_Path,
        #             File_Size,
        #             Transfer_Time,
        #             "None" as Ingest_Path,
        #             "None" as Ingest_Time,
        #             0.0 as Delta_Time
        #         FROM TRANSFER_LIST 
        #         WHERE 
        #             FILENUM not in (select FILENUM from Ingest_list) and 
        #             Nite_Trans = "{self.nite}" 
        #         ORDER BY Transfer_Time
        #     ''',
        #         f'''
        #         SELECT 
        #             Transfer_Path,
        #             File_Size,
        #             Transfer_Time,
        #             Ingest_Path,
        #             Ingest_Time,
        #             printf("%.1f",(julianday(Ingest_Time)-julianday(Transfer_Time))*24*3600.) as Delta_Time 
        #         FROM 
        #             INGEST_LIST i,
        #             TRANSFER_LIST t 
        #         WHERE 
        #             i.FILENUM = t.FILENUM and Nite_Obs = "{self.nite}" 
        #         ORDER BY Transfer_Time
        #     '''
        #     ])
            try:
                # Render table template after populating with query results
                with open(os.path.join(os.path.dirname(__file__), "templates/nite.tpl.html")) as f:
                    templateText = f.read()
                template = Template(templateText)
                html = template.render(
                    html_head=html_head,
                    name=self.name,
                    nowstr=self.nowstr,
                    nite=self.nite,
                    storage=self.storage,
                    repo_dir=self.repo_dir,
                    data=data,
                    gen3=gen == 3,
                    missing_images=missing_images,
                )
                # log.debug(f'{html}')
            except Exception as e:
                log.error(f'{str(e)}')
                html = f'{str(e)}'

            with open(outfilename, 'w') as outf:
                outf.write(html)

    def update_source_html(self):
            
        for gen in [2, 3]:
            log.debug(f'''\n**********************************\nupdate_source_html: gen{gen}\n**********************************\n''')
            file_count_table = f'FILE_COUNT_GEN{gen}'
            if gen == 3:
                outfilename = f'{self.output_dir}/index.html'
                modifier = ''
            else:
                outfilename = f'{self.output_dir}/index_gen2.html'
                modifier = '_gen2'
            try:
                # Render table template after populating with query results
                with open(os.path.join(os.path.dirname(__file__), "templates/source.tpl.html")) as f:
                    templateText = f.read()
                template = Template(templateText)
                html = template.render(
                    html_head=html_head,
                    name=self.name,
                    nowstr=self.nowstr,
                    data=db_to_html(
                        self.db,
                        f'''select * from {file_count_table} ORDER by Nite_Obs DESC''',
                        linkify=True,
                        modifier=modifier,
                    ),
                    gen3=gen == 3,
                )
                # log.debug(f'{html}')
            except Exception as e:
                log.error(f'{str(e)}')
                html = f'{str(e)}'

            with open(outfilename, 'w') as outf:
                outf.write(html)


async def main():
    config = get_config()
    tim = TransferIngestMonitor(config)

    await tim.query_efd()
    tim.query_consolidated_db()
    tim.update_monitor_db()
    for num in range(tim.num_days):
        tim.set_date(num)
        tim.compile_info_per_night()
        tim.update_nite_html()
    tim.update_source_html()

asyncio.run(main())
