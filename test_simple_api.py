#!/usr/bin/env python
import requests
import json

# Test the simple test endpoint
url = 'http://localhost:8000/api/test/'

print(f"Testing simple endpoint: {url}")

try:
    # Test GET request
    response = requests.get(url)
    print(f"GET Status code: {response.status_code}")
    print(f"GET Response: {response.text}")
    
    # Test POST request (like the frontend does)
    response = requests.post(url, json={}, headers={'Content-Type': 'application/json'})
    print(f"POST Status code: {response.status_code}")
    print(f"POST Response: {response.text}")
    
except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to local server. Is it running?")
except Exception as e:
    print(f"ERROR: {e}")
