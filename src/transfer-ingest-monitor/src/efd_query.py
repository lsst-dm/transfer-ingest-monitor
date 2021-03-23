from astropy.time import Time, TimeDelta
from lsst_efd_client import EfdClient
import asyncio

client = EfdClient('ldf_int_efd')
cl = efd.influx_client

t2_agg = Time('2021-03-15T12:00:00', scale='tai')
t1_agg = t2_agg - TimeDelta(5*24*3600, format='sec', scale='tai') # look back over 5 days of data

t2_chunk = Time('2021-03-04T12:00:00', scale='tai')
t1_chunk = Time('2021-02-04T12:00:00', scale='tai')

def make_query_str(beg, end, interval):
    return ("SELECT mean(\"ambient_temp\") as \"temp\", mean(\"pressure\") as \"pressure\", mean(\"humidity\") as \"humidity\" " +
            "FROM \"efd\".\"autogen\".\"lsst.sal.WeatherStation.weather\" " +
            f"WHERE time > '{beg.isot}Z' and time <= '{end.isot}Z' " +
            f"GROUP BY time({interval})")
            
async def get_topics():
    topics = await client.get_topics()
    print(topics)
    return topics
    
async def query_topic(topic='lsst.sal.ATCamera.wreb'):
    t2 = Time('2021-03-01T12:00:00', scale='tai')
    t1 = t2 - TimeDelta(15*24*3600, format='sec', scale='tai')
    df = await client.select_time_series(topic, '*', t1, t2)
    print(df.head())
    
async def submit_query():
    result = await cl.query(make_query_str(t1_agg, t2_agg, '30m'))
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    tasks = [
        # loop.create_task(get_topics()),
        loop.create_task(query_topic(topic='lsst.sal.ATCamera.command_takeImages')),
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
