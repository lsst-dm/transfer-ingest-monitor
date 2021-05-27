from astropy.time import Time, TimeDelta
from lsst_efd_client import EfdClient
import asyncio
from datetime import datetime
import pandas as pd

client = EfdClient('ldf_stable_efd')
cl = client.influx_client

t2_agg = Time('2021-03-24T12:00:00', scale='tai')
t1_agg = t2_agg - TimeDelta(15*24*3600, format='sec', scale='tai')


def make_query_str(beg, end, interval):
    # query = f'''
    #         SELECT "expTime"
    #         FROM "efd"."autogen"."lsst.sal.ATCamera.command_takeImages"
    #         WHERE time > '{beg.isot}Z' and time <= '{end.isot}Z'
    #         '''
    query = f'''
            SELECT 
                "imageName",
                "imageDate",
                "imageIndex",
                "private_sndStamp",
                "private_rcvStamp",
                "timestampAcquisitionStart",
                "timestampEndOfReadout",
                "imageSource",
                "imagesInSequence"
            FROM "efd"."autogen"."lsst.sal.ATCamera.logevent_endReadout" 
            WHERE time > '{beg.isot}Z' and time <= '{end.isot}Z' 
            '''
    print(query)
    return query


async def get_topics():
    topics = await client.get_topics()
    print(topics)
    return topics


async def query_topic(topic='lsst.sal.ATCamera.wreb'):
    t2 = Time('2020-03-16T12:00:00', scale='tai')
    t1 = t2 - TimeDelta(15*24*3600, format='sec', scale='tai')
    print('Querying EFD...')
    df = await client.select_time_series(topic, '*', t1, t2)
    print(df.head())


async def submit_query():
    result = await cl.query(make_query_str(t1_agg, t2_agg, '30m'))
    print(result)
    for index, row in result.iterrows():
        print(f'''
        imageName: {row['imageName']}
        imageDate: {row['imageDate']}
        timestampAcquisitionStart: {row['timestampAcquisitionStart']} --> {datetime.fromtimestamp(row['timestampAcquisitionStart']).strftime("%m-%d-%YT%H:%M:%S.%f %z")}
        timestampEndOfReadout: {row['timestampEndOfReadout']} --> {datetime.fromtimestamp(row['timestampEndOfReadout']).strftime("%m-%d-%YT%H:%M:%S.%f %z")}
        ''')
    return result

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    tasks = [
        # loop.create_task(get_topics()),
        # loop.create_task(query_topic(topic='lsst.sal.ATCamera.wreb')),
        loop.create_task(submit_query()),
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
