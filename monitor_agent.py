import time
import psutil
import requests
from influxdb_client import InfluxDBClient, Point, WriteOptions

# InfluxDB settings
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "_ngsl81ZgEW-zivbImIl6kjANpltSdb6Pu-SPe116a7tBk7epMizCTHN2NgO8-xfNsrhaOTNijZRg352HS4V4w=="
INFLUX_ORG = "gotn"
INFLUX_BUCKET = "gotn-metrics"

# Ollama/Mistral settings
MISTRAL_URL = "http://localhost:11434/api/generate"
MISTRAL_KEEPALIVE_MODEL = "mistral"  # adjust to your model name

# Streamlit app settings
STREAMLIT_URL = "http://localhost:8501"

# Initialize Influx client
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
write_api = client.write_api(write_options=WriteOptions(batch_size=1))

def keep_mistral_alive():
    payload = {
        "model": MISTRAL_KEEPALIVE_MODEL,
        "prompt": "ping",
        "stream": False
    }
    try:
        requests.post(MISTRAL_URL, json=payload, timeout=10)
        print("[Mistral] Keepalive sent.")
    except Exception as e:
        print(f"[Mistral] Keepalive failed: {e}")

def test_streamlit_load():
    try:
        start = time.time()
        response = requests.get(STREAMLIT_URL, timeout=10)
        latency = (time.time() - start) * 1000  # milliseconds
        if response.status_code == 200:
            print(f"[Streamlit] Loaded in {latency:.2f}ms")
            return latency
        else:
            print(f"[Streamlit] Bad status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"[Streamlit] Load test failed: {e}")
        return None

def collect_system_metrics():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    print(f"[System] CPU: {cpu}%, Memory: {memory}%, Disk: {disk}%")
    return cpu, memory, disk

def write_metrics_to_influx(cpu, memory, disk, streamlit_latency):
    point = Point("server_metrics") \
        .field("cpu_percent", cpu) \
        .field("memory_percent", memory) \
        .field("disk_percent", disk)

    if streamlit_latency is not None:
        point.field("streamlit_latency_ms", streamlit_latency)

    write_api.write(bucket=INFLUX_BUCKET, record=point)
    print("[InfluxDB] Metrics written.")

def main():
    last_mistral_keepalive = time.time()

    while True:
        now = time.time()

        # Every 5 minutes, keep Mistral alive
        if now - last_mistral_keepalive >= 300:
            keep_mistral_alive()
            last_mistral_keepalive = now

        # Every 10 seconds
        streamlit_latency = test_streamlit_load()
        cpu, memory, disk = collect_system_metrics()
        write_metrics_to_influx(cpu, memory, disk, streamlit_latency)

        time.sleep(10)

if __name__ == "__main__":
    main()

