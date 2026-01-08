import requests

try:
    response = requests.get('http://localhost:8001/api/v1/current-state')
    data = response.json()
    if 'gpu_temps' in data and len(data['gpu_temps']) > 0:
        gpu = data['gpu_temps'][0]
        print(f'GPU {gpu["gpu_id"]}: {gpu["temperature"]:.1f}°C, workload: {gpu.get("workload", "N/A")}')
    else:
        print('No GPU data')
except Exception as e:
    print(f'Error: {e}')