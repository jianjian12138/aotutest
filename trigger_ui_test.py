import requests

# get first test case
try:
    cases_resp = requests.get('http://127.0.0.1:4545/api/ui-automation/test-cases/')
    cases = cases_resp.json()
    if 'results' in cases:
        cases = cases['results']
    
    if not cases:
        print("No test cases found")
        exit(0)
        
    case_id = cases[0]['id']
    print(f"Triggering execution for case {case_id}...")
    
    # execute
    run_resp = requests.post(f'http://127.0.0.1:4545/api/ui-automation/test-cases/{case_id}/run/', 
                             json={"engine": "playwright", "browser": "chrome", "headless": True})
    
    print(f"Status Code: {run_resp.status_code}")
    print(f"Response:")
    print(run_resp.text)
except Exception as e:
    print(f"Error: {e}")
