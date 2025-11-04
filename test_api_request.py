#!/usr/bin/env python
import requests
import json

# Test the API endpoint directly
url = 'http://localhost:8000/api/sonden-options/'
data = {
    'schachttyp': 'GN R Kompakt',
    'hvb_size': '63'
}

print(f"Testing API endpoint: {url}")
print(f"Request data: {data}")

try:
    response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        response_data = response.json()
        print(f"Parsed response: {response_data}")
        print(f"Number of options: {len(response_data.get('sonden_options', []))}")
    
except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to local server. Is it running?")
except Exception as e:
    print(f"ERROR: {e}")
