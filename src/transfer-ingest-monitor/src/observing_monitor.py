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
    parser.add('--gen', action='store', type=int, required=False, default=2, choices=[2,3],
               help='Generation butler (2 or 3) supported.')
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
                self.data_source = [src for src in data_sources if src['name'] == config['source_name']][0]
        except Exception as e:
            log.error(str(e))
            log.error(f"""Could not determine database for source named "{config['source_name']}". Exiting""")
            sys.exit(1)

        # Set the data source name
        self.name = config['source_name']
        self.gen = config['gen']
        
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
            CREATE TABLE IF NOT EXISTS FILE_COUNT (
                Nite_Obs TEXT PRIMARY KEY, 
                Last_Update TEXT, 
                N_Files INTEGER, 
                Last_Transfer TEXT, 
                N_Ingest INTEGER, 
                N_Small INTEGER, 
                N_Not_Fits, 
                N_Error INTEGER, 
                Last_Ingest TEXT
            )
        ''')
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
                Last_Ingest TEXT
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
                Err_Message TEXT
            )'''
        )
        c.execute('''
            CREATE TABLE IF NOT EXISTS TRANSFER_LIST (
                Filenum INTEGER PRIMARY KEY,
                Nite_Trans TEXT,
                Last_Update TEXT,
                Transfer_Path TEXT,
                Transfer_Time TEXT,
                File_Size INT
            )'''
        )
        c.execute('''
            CREATE TABLE IF NOT EXISTS INGEST_LIST (
                FILENUM INTEGER PRIMARY KEY,
                Ingest_Path TEXT,
                Nite_Obs TEXT,
                Last_Update TEXT,
                Ingest_Time TEXT
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
        log.debug(f"Current night: {self.nite}")

    def count_new_files(self, dir_list=[]):
        self.nfiles = 0
        self.filenames = []
        self.tdevs = []
        self.tinos = []
        self.tpaths = []
        self.ttimes = []
        self.ttimestrs = []
        self.tnites = []
        self.filesizes = []
        if dir_list == []:
            # dir_list = [self.nite, self.nite_no_hyphen, self.next_nite, self.next_nite_no_hyphen]
            dir_list = [self.nite, self.nite_no_hyphen]
        for dir in dir_list:
            if dir in [self.next_nite, self.next_nite_no_hyphen]:
                nite = self.next_nite
            else:
                nite = self.nite
            dirfile = 0
            if os.path.exists(os.path.join(self.storage, dir)):
                for file in [os.path.join(dir, fn) for fn in sorted(rec_listdir(os.path.join(self.storage, dir)))]:
                    file_path = os.path.join(self.storage, file)
                    ttime = os.path.getmtime(file_path)
                    file_stat = os.stat(file_path)
                    self.filenames.append(file)
                    self.tpaths.append(file_path)
                    self.tdevs.append(file_stat.st_dev)
                    self.tinos.append(file_stat.st_ino)
                    self.filesizes.append(file_stat.st_size)
                    self.ttimes.append(ttime)
                    self.ttimestrs.append(datetime.utcfromtimestamp(ttime).strftime('%Y-%m-%dT%H:%M:%S'))
                    self.tnites.append(nite)
                    self.nfiles += 1
                    dirfile += 1


    async def query_efd(self):

        
        first_nite = Time(f'{self.first_day.strftime("%Y-%m-%d")}T00:00:00', scale='tai')
        last_nite  = Time(f'{self.last_day.strftime("%Y-%m-%d")}T00:00:00', scale='tai')
        self.image_data = []
        self.images_missing_in_archiver = []
        try:
            table_name_archiver = self.data_source['efd']['tables']['archiver']
            table_name_camera = self.data_source['efd']['tables']['camera']
            cl = EfdClient(self.data_source['efd']['host']).influx_client
        except:
            return
        query = f'''
            SELECT 
                "imageName",
                "timestampEndOfReadout"
            FROM "efd"."autogen"."{table_name_camera}"
            WHERE time >= '{first_nite.isot}Z' AND time < '{last_nite.isot}Z'
        '''
        # log.debug(query)
        result = await cl.query(query)
        # For each image taken by the camera, find the associated record in the archiver
        if len(result) > 0:
            for index, row in result.iterrows():
                log.debug(f'Row {index}:\n{row}')
                try:
                    imageName = row['imageName']
                    creation_timestamp = row['timestampEndOfReadout']
                    creation_time = datetime.fromtimestamp(creation_timestamp).strftime("%Y-%m-%dT%H:%M:%S")
                    query2 = f'''
                        SELECT 
                            "obsid",
                            "raft",
                            "sensor"
                        FROM "efd"."autogen"."{table_name_archiver}"
                        WHERE obsid = '{imageName}' AND raft != '' AND sensor != ''
                    '''
                    # log.debug(query2)
                    result2 = await cl.query(query2)
# 
                    if len(result2) > 0:
                        for index, row2 in result2.iterrows():
                            log.debug(f'Row {index}:\n{row2}')
                            try:
                                zero_pad_sensor = '0' if len(row2['sensor']) == 1 else ''
                                zero_pad_raft = '0' if len(row2['raft']) == 1 else ''
                                filename = f'''{row2['obsid']}{self.data_source['filename']['raft_separator']}R{zero_pad_raft}{row2['raft']}{self.data_source['filename']['sensor_separator']}S{zero_pad_sensor}{row2['sensor']}.fits'''
                                self.image_data.append({
                                    'timestamp': creation_timestamp,
                                    'created_time': creation_time,
                                    'filename': filename,
                                    'imageName': imageName,
                                })
                                log.debug(f'{self.image_data[-1]}')
                            except Exception as e:
                                log.error(f'Error displaying row: {str(e)}')
                    else:
                        # If the image is not found in the archiver, this is probably an error that should be reported.
                        self.images_missing_in_archiver.append({
                            'imageName': imageName,
                        })
                except Exception as e:
                    log.error(f'Error displaying row: {str(e)}')
        if self.images_missing_in_archiver:
            log.warning(f'''Images missing in archiver table:\n{self.images_missing_in_archiver}''')

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
                    {self.data_source['consolidated_db']['files_table']}, 
                    {self.data_source['consolidated_db']['file_events_table']}
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
        
        # TODO: remove ctimes
        # self.ctimes = np.array(len(df)*['0000-00-00T00:00:00.00'])
        
        # Basic metadata
        self.ids = np.array(df['id'], dtype=int)
        self.paths = np.array(df['path'])
        self.filenames = np.array(df['filename'])
        
        # nites captures a simplified timestamp for the day on which the DBB Endpoint Manager DB discovered the file
        self.nites = np.array(len(df)*['0000-00-00'])
        
        # Status of ingest attempt
        self.statuss = np.array(df['status'])

        # ttime is the time the file was discovered by the DBB Endpoint Manager DB
        self.ttimes = np.array(df['ttime'])

        # itime is the start time of the most recent event. Usually, there are three events for each file:
        # (1) file was added to the "waiting list", status UNTRIED;
        # (2) file was selected for ingestion, status: PENDING;
        # (3) ingest attempt was made, status can be either SUCCESS, FAILURE, or UNKNOWN. Each event is timed individually.
        self.itimes = np.array(df['itime'])

        # Duration is how long the ingestion took (usually negligible)
        self.durations = np.array(df['duration'])

        # File size
        self.filesizes = np.array(df['size_bytes'])
        # Error message associated with FAILURE events
        self.err_messages = np.array(df['err_message'])
        self.err_messages[self.err_messages == None] = ''
        
        # Process each record
        for num in range(len(df)):
            full_path = os.path.join(self.storage, self.paths[num])
            self.ttimes[num] = self.ttimes[num].replace(' ', 'T')
            self.itimes[num] = self.itimes[num].replace(' ', 'T')
            if not os.path.exists(full_path):
            #    self.filesizes[num] = (os.stat(full_path).st_size)
            # TODO: remove ctimes
            #    self.ctimes[num] = datetime.utcfromtimestamp(os.lstat(full_path).st_ctime).strftime('%Y-%m-%dT%H:%M:%S.%f')
            #    if self.ctimes[num] < self.ttimes[num]:
            #        self.nites[num] = (datetime.strptime(self.ctimes[num], '%Y-%m-%dT%H:%M:%S.%f')-timedelta(hours=12)).strftime('%Y-%m-%d')
            # else:
                log.warning(f'''File path not found: "{full_path}"''')
            # Determine the date of the transfer from the file path. If not
            self.nites[num] = parse_date_from_path(self.paths[num].split('/')[0])
            if not self.nites[num]:
                self.nites[num] = (datetime.strptime(self.ttimes[num], '%Y-%m-%dT%H:%M:%S.%f')-timedelta(hours=12)).strftime('%Y-%m-%d')

    def count_links(self):
        self.ltimes = []
        self.ltimestrs = []
        self.ltimetttt = []
        self.lpaths = []
        self.ldevs = []
        self.linos = []
        self.lfilepaths = []
        self.lnites = []
        self.nlinks = 0
        conn = sqlite3.connect(self.repo)
        c = conn.cursor()
        query = 'PRAGMA table_info(raw)'
        c.execute(query)
        columns = [element[1].lower() for element in c.fetchall()]
        # Does this table have raftname (BOT, comcam) or not (auxtel)?
        if 'raftname' in columns:
            select_statement = f"""
                dayObs||'/'||expId||'/'||expid||'-'|| raftname ||'-'|| detectorName||'-det'||printf('%03d', detector)||'.fits'
            """
        else:
            select_statement = f"""
                dayObs||'/'||expid||'-det'||printf('%03d', detector)||'.fits'
            """
        query = f"""
            SELECT {select_statement} as FILENAME  
            FROM raw 
            WHERE dayObs = '{self.nite}' 
            ORDER by FILENAME
        """

        c.execute(query)
        rows = c.fetchall()
        conn.close()
        for file_name in [row[0] for row in rows]:
            full_path = os.path.join(self.raw_dir, file_name)
            if os.path.exists(full_path):
                self.ltimes.append(os.lstat(full_path).st_atime)
                self.ltimestrs.append(datetime.utcfromtimestamp(self.ltimes[-1]).strftime('%Y-%m-%dT%H:%M:%S'))
                self.lpaths.append('raw/'+file_name)
                file_stat = os.stat(full_path)
                self.ldevs.append(file_stat.st_dev)
                self.linos.append(file_stat.st_ino)
                if os.path.islink(full_path):
                    file_path = os.readlink(full_path)
                    self.lfilepaths.append(file_path.split('storage/')[-1])
                else:
                    # Slow findpath replaced once we started writing down FILENUM (st_dev, st_iso combos)
                    #                    FILEPATH=findpath(FULLPATH,self.storage)
                    self.lfilepaths.append('NONE')
                self.lnites.append(self.nite)
                self.nlinks += 1
            else:
                log.warning(full_path+' does not exist.')
        log.debug(f'''{self.name} (gen {self.gen}): {str(self.nlinks)} found for {self.nite}.''')

    def count_links_search(self, dirlist=[]):
        self.ltimes = []
        self.ltimestrs = []
        self.lpaths = []
        self.ldevs = []
        self.linos = []
        self.lfilepaths = []
        self.lnites = []
        self.nlinks = 0
        repodirs = ['raw']

        def samelink(file1, file2):
            s1 = os.stat(file1)
            s2 = os.stat(file2)
            return (s1.st_ino, s1.st_dev) == (s2.st_ino, s2.st_dev)

        def findpath(file1, storage_dir):
            for file2 in glob.glob(storage_dir+'/*/*.fits'):
                if samelink(file1, file2):
                    return(file2)
            return 'None'

        def timetonite(time):
            return (datetime.utcfromtimestamp(time)-timedelta(hours=12)).strftime('%Y-%m-%d')

        def dirisnite(dir):
            if not dir[:4].isdigit():
                return False
            if not dir[-2:].isdigit():
                return False
            if len(dir) == 10:
                if not (dir[4] == '-' and dir[7] == '-'):
                    return False
                if dir[5:7].isdigit():
                    return True
            if len(dir) == 8:
                if dir[4:6].isdigit():
                    return True
            return False

        if dirlist == []:
           dirlist = [os.path.join(repodir, self.nite) for repodir in repodirs]
        for dir_name in dirlist:
            nite_dir = os.path.join(self.repo_dir, dir_name)
            if os.path.exists(nite_dir):
                for file in sorted(rec_listdir(nite_dir)):
                    full_path = nite_dir+'/'+file
                    self.ltimes.append(os.lstat(full_path).st_atime)
                    path_stat = os.stat(full_path)
                    self.ldevs.append(path_stat.st_dev)
                    self.linos.append(path_stat.st_ino)
                    self.ltimestrs.append(datetime.utcfromtimestamp(self.ltimes[-1]).strftime('%Y-%m-%dT%H:%M:%S'))
                    self.lpaths.append(dir_name+'/'+file)
                    if os.path.islink(full_path):
                        file_path = os.readlink(full_path)
                    else:
                        file_path = findpath(full_path, self.storage)
                    self.lfilepaths.append(file_path.split('storage/')[-1])
                    if dirisnite(dir_name.split('/')[-1]):
                        self.lnites.append(self.nite)
                    else:
                        self.lnites.append(timetonite(os.path.getmtime(file_path)))
                    self.nlinks += 1
            else:
                log.warning(f"Warning: {nite_dir} does not exist.")

    def update_db_files(self):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        for num in range(len(self.filenames)):
            c.execute(f'''
                INSERT OR REPLACE INTO TRANSFER_LIST (
                    Filenum, 
                    Nite_Trans, 
                    Last_Update, 
                    Transfer_Path, 
                    Transfer_Time, 
                    File_Size
                ) VALUES(
                   {str(self.tinos[num]*10000+self.tdevs[num])}, 
                   '{self.tnites[num]}', 
                   '{self.nowstr}', 
                   '{self.filenames[num]}', 
                   '{self.ttimestrs[num]}', 
                   {str(self.filesizes[num])}
                )
            ''')
        conn.commit()
        conn.close()
        if len(self.filenames) > 0:
            log.info(f"Inserted or replaced {len(self.filenames)} into TRANSFER_LIST.")

    def update_monitor_db(self):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        # log.debug(f'IDs: {self.ids}')
        # log.debug(f'''Image search: "{[image['filename'] for image in self.image_data]}"''')
        images_recorded = 0
        for image in self.image_data:
            log.debug(f'''Image search. Image : "{image}"''')
            # Cross-match the consolidated db records with the EFD image data records
            search = [idx for idx, filename in enumerate(self.filenames) if image['filename'] == filename ]
            if not search:
                log.warning(f'''Image file not found in consolidated db: "{image['filename']}"''')
                continue
            if len(search) > 1:
                log.warning(f'''More than one filename matches the image "{image['filename']}":\n{search}''')
            # Insert or update the file information in the monitor db
            idx = search[0]
            query = f'''
                INSERT OR REPLACE INTO FILE_LIST_GEN3 (
                    Filenum, 
                    Nite, 
                    Last_Update, 
                    Transfer_Path, 
                    Status, 
                    Creation_Time, 
                    Discovery_Time, 
                    Ingest_Time, 
                    File_Size, 
                    Err_Message
                ) VALUES(
                    :ids,
                    :nites,
                    :now,
                    :paths,
                    :statuss,
                    :created_time,
                    :ttimes,
                    :itimes,
                    :filesizes, 
                    :errmsg
                )
                '''
            # log.debug(f'Query:\n{query}')
            c.execute(query, {
                'ids': str(self.ids[idx]),
                'nites': self.nites[idx],
                'now': self.nowstr,
                'paths': self.paths[idx],
                'statuss': self.statuss[idx],
                'created_time': image['created_time'],
                'ttimes': self.ttimes[idx],
                'itimes': self.itimes[idx],
                'filesizes': str(self.filesizes[idx]),
                'errmsg': self.err_messages[idx],
            })
            images_recorded += 1
        conn.commit()
        conn.close()
        if len(self.ids) > 0:
            log.info(f"Inserted or replaced {images_recorded} into FILE_LIST_GEN3.")

    def update_db_links(self):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        for num in range(len(self.lpaths)):
            c.execute(f'''
                INSERT OR REPLACE INTO INGEST_LIST (
                    Filenum, 
                    Ingest_Path, 
                    Nite_Obs, 
                    Last_Update, 
                    Ingest_Time) 
                VALUES(
                    {str(self.linos[num]*10000+self.ldevs[num])}, 
                    '{self.lpaths[num]}', 
                    '{self.lnites[num]}', 
                    '{self.nowstr}', 
                    '{self.ltimestrs[num]}'
                )
            ''')
        conn.commit()
        conn.close()
        if len(self.lpaths) > 0:
            log.info(f"Inserted or replaced {len(self.lpaths)} into INGEST_LIST.")

    def compile_info_per_night(self):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        sizemin = '10000'
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
            FROM FILE_LIST_GEN3 t 
            WHERE Nite = "{self.nite}" 
            GROUP BY Nite
        ''')
        rows = c.fetchall()
        if len(rows) > 0:
            [self.ntransfer, self.maxctime, self.ningest, self.maxttime, self.maxitime, self.nnotfits, self.nsmall, self.nerror] = rows[0]
        else:
            [self.ntransfer, self.maxctime, self.ningest, self.maxttime, self.maxitime, self.nnotfits, self.nsmall, self.nerror] = [0, '0000-00-00T00:00:00', 0, '0000-00-00T00:00:00', '0000-00-00T00:00:00', 0, 0, 0]
        c.execute(f'''
            INSERT OR REPLACE INTO FILE_COUNT_GEN3 (
                Nite_Obs,
                Last_Update,
                N_Files,
                Last_Creation,
                N_Ingest,
                N_Small,
                N_Not_Fits,
                N_Error,
                Last_Discovery,
                Last_Ingest
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
                '{self.maxitime}'
                )
        ''')
        conn.commit()
        conn.close()

    def get_night_data(self):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute(f'''
            SELECT 
                count(Ingest_Path),
                max(Transfer_Time),
                max(Ingest_Time) 
            FROM 
                INGEST_LIST i,
                TRANSFER_LIST t 
            WHERE 
                i.FILENUM = t.FILENUM 
                AND 
                Nite_Obs = "{self.nite}" 
            GROUP by Nite_Obs
        ''')
        rows = c.fetchall()
        if len(rows) > 0:
            [self.ningest, self.maxttime, self.maxitime, ] = rows[0]
        else:
            [self.ningest, self.maxttime, self.maxitime] = [0, '0000-00-00T00:00:00', '0000-00-00T00:00:00']
        sizemin = '10000'
        c.execute(f'''
            SELECT 
                count(FILENUM), 
                max(Transfer_Time), 
                sum(File_Size < '+sizemin+'), 
                sum(substr(Transfer_Path,-5) != ".fits"), 
                sum((substr(Transfer_Path,-5) == ".fits")*(File_Size > {sizemin})) 
            FROM TRANSFER_LIST 
            WHERE FILENUM not in (select FILENUM from INGEST_LIST) and Nite_Trans = "{self.nite}" 
            GROUP BY Nite_Trans
        ''')
        rows = c.fetchall()
        if len(rows) > 0:
            [ntransfer_unmatched, maxttime, self.nsmall, self.nnotfits, self.nerror] = rows[0]
            self.ntransfer = self.ningest+ntransfer_unmatched
            self.maxttime = max(self.maxttime, maxttime)
        else:
            self.ntransfer = self.ningest
            [self.nsmall, self.nnotfits, self.nerror] = [0, 0, 0]
        c.execute(f"""
            INSERT OR REPLACE INTO FILE_COUNT (
                Nite_Obs, 
                Last_Update, 
                N_Files,
                Last_Transfer,
                N_Ingest,
                N_Small,
                N_Not_Fits,
                N_Error,
                Last_Ingest
            ) VALUES(
                '{self.nite}', 
                '{self.nowstr}', 
                {str(self.ntransfer)}, 
                '{self.maxttime}', 
                {str(self.ningest)}, 
                {str(self.nsmall)}, 
                {str(self.nnotfits)}, 
                {str(self.nerror)}, 
                '{self.maxitime}'
            )
        """)
        conn.commit()
        conn.close()

    def update_nite_html(self, gen3=False):
        if gen3:
            outfilename = f'{self.output_dir}/{self.nite}.html'
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
                FROM FILE_LIST_GEN3 
                WHERE Nite = "{self.nite}" 
                ORDER BY Creation_Time
            '''
            ])
        else:
            outfilename = f'{self.output_dir}/{self.nite}_gen2.html'
            data = db_to_html(self.db, [
                f'''
                SELECT 
                    Transfer_Path,
                    File_Size,
                    Transfer_Time,
                    "None" as Ingest_Path,
                    "None" as Ingest_Time,
                    0.0 as Delta_Time
                FROM TRANSFER_LIST 
                WHERE 
                    FILENUM not in (select FILENUM from Ingest_list) and 
                    Nite_Trans = "{self.nite}" 
                ORDER BY Transfer_Time
            ''',
                f'''
                SELECT 
                    Transfer_Path,
                    File_Size,
                    Transfer_Time,
                    Ingest_Path,
                    Ingest_Time,
                    printf("%.1f",(julianday(Ingest_Time)-julianday(Transfer_Time))*24*3600.) as Delta_Time 
                FROM 
                    INGEST_LIST i,
                    TRANSFER_LIST t 
                WHERE 
                    i.FILENUM = t.FILENUM and Nite_Obs = "{self.nite}" 
                ORDER BY Transfer_Time
            '''
            ])
        try:
            # Render table template after populating with query results
            with open(os.path.join(os.path.dirname(__file__), "nite.tpl.html")) as f:
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
                gen3=gen3,
            )
            # log.debug(f'{html}')
        except Exception as e:
            log.error(f'{str(e)}')
            html = f'{str(e)}'

        with open(outfilename, 'w') as outf:
            outf.write(html)

    def update_main_html(self, gen3=False):
        file_count_table = 'FILE_COUNT'
        outfilename = f'{self.output_dir}/index_gen2.html'
        modifier = '_gen2'
        if gen3:
            file_count_table += '_GEN3'
            outfilename = f'{self.output_dir}/index.html'
            modifier = ''
        try:
            # Render table template after populating with query results
            with open(os.path.join(os.path.dirname(__file__), "main.tpl.html")) as f:
                templateText = f.read()
            template = Template(templateText)
            html = template.render(
                html_head=html_head,
                name=self.name,
                nowstr=self.nowstr,
                data=db_to_html(
                    self.db,
                    f'select * from {file_count_table} ORDER by Nite_Obs DESC',
                    linkify=True,
                    modifier=modifier
                ),
                gen3=gen3,
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

    if tim.gen == 2:
        for num in range(tim.num_days):
            tim.set_date(num)
            tim.count_new_files()
            tim.update_db_files()
            if config['search_links']:
                tim.count_links_search()
            else:
                tim.count_links()
            tim.update_db_links()
        for num in range(tim.num_days):
            tim.set_date(num)
            tim.get_night_data()
            tim.update_nite_html()
        tim.update_main_html()
    if tim.gen == 3:
        await tim.query_efd()
        tim.query_consolidated_db()
        for num in range(tim.num_days):
            tim.set_date(num)
            tim.update_monitor_db()
            tim.compile_info_per_night()
            tim.update_nite_html(gen3=True)
        tim.update_source_html(gen3=True)

asyncio.run(main())
