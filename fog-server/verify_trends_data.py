import sys
import os
import time
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

try:
    import config
except ImportError:
    # Quick mock if config not found (assuming default)
    class Config:
        INFLUXDB_URL = "http://localhost:8086"
        INFLUXDB_TOKEN = "my-super-secret-auth-token"
        INFLUXDB_ORG = "diploma_org"
        INFLUXDB_BUCKET = "gpu_cooling"
    config = Config()

def check_and_inject():
    print(f"Connecting to {config.INFLUXDB_URL}, Org: {config.INFLUXDB_ORG}, Bucket: {config.INFLUXDB_BUCKET}")
    
    client = InfluxDBClient(
        url=config.INFLUXDB_URL,
        token=config.INFLUXDB_TOKEN,
        org=config.INFLUXDB_ORG
    )
    
    query_api = client.query_api()
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    # 1. Query existing data
    query = f'''
    from(bucket: "{config.INFLUXDB_BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r["_measurement"] == "advanced_trends")
      |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
      |> limit(n: 5)
    '''
    
    print("Querying existing data...")
    try:
        result = query_api.query(query=query)
        count = 0
        for table in result:
            for record in table.records:
                count += 1
                print(f"Found point: Time={record.get_time()}, CI={record.values.get('corrosion_index')}, FWI={record.values.get('fan_wear_index')}")
        
        print(f"Total points found in last 24h: {count}")
        
        if count == 0:
            print("No data found! Injecting mock data...")
            points = []
            valid_time = datetime.now(timezone.utc)
            
            for i in range(10):
                t = valid_time - timedelta(minutes=30 * (10-i))
                ci = 0.5 + (i * 0.1)
                fwi = 10 + (i * 5)
                
                point = Point("advanced_trends") \
                    .tag("device_id", "mock_device") \
                    .field("corrosion_index", float(ci)) \
                    .tag("ci_risk", "low" if ci < 1.0 else "medium") \
                    .field("fan_wear_index", float(fwi)) \
                    .tag("fwi_wear", "normal") \
                    .time(t)
                points.append(point)
            
            write_api.write(bucket=config.INFLUXDB_BUCKET, record=points)
            print(f"Injected {len(points)} mock points.")
            print("Please refresh the web page.")
            
        else:
            print("Data exists! The graph should not be empty.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    check_and_inject()
