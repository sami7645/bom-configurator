#!/usr/bin/env python
import requests
import json

# Test the sonden-options endpoint with detailed debugging
url = 'http://localhost:8000/api/sonden-options/'

test_cases = [
    {'schachttyp': 'GN R Kompakt', 'hvb_size': '63'},
    {'schachttyp': 'GN X1', 'hvb_size': '75'},
    {'schachttyp': 'GN R Nano', 'hvb_size': '63'},
    {'schachttyp': '', 'hvb_size': '63'},  # Test empty schachttyp
    {'schachttyp': 'GN R Kompakt', 'hvb_size': ''},  # Test empty hvb_size
]

print(f"Testing sonden-options endpoint: {url}")

for i, data in enumerate(test_cases, 1):
    print(f"\n=== Test Case {i} ===")
    print(f"Request data: {data}")
    
    try:
        response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            options_count = len(response_data.get('sonden_options', []))
            print(f"Number of options returned: {options_count}")
            
            if options_count > 0:
                print("Options:")
                for option in response_data['sonden_options']:
                    print(f"  - {option['durchmesser_sonde']}mm - {option['artikelbezeichnung']}")
            else:
                print("No options returned (this would show 'Keine Optionen verfügbar')")
        
    except Exception as e:
        print(f"ERROR: {e}")

print("\n=== Summary ===")
print("If any test case returns 0 options when it should return options,")
print("that's the bug we need to fix!")
