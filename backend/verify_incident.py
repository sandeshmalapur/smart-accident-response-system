import httpx

def check():
    r = httpx.post('http://localhost:8000/api/v1/auth/login', json={'email':'admin@example.com','password':'changeme123'})
    tok = r.json()['access_token']
    headers = {'Authorization': f'Bearer {tok}'}
    
    # Query specifically for accident incidents
    incs = httpx.get('http://localhost:8000/api/v1/incidents?incident_type=accident', headers=headers).json()
    print(f'Total accident incidents: {len(incs)}')
    for inc in incs[:3]:
        inc_id = inc['id']
        det = httpx.get(f'http://localhost:8000/api/v1/incidents/{inc_id}', headers=headers).json()
        print('--- Accident Incident ---')
        print('Incident ID:', det['id'])
        print('Type:', det['incident_type'])
        print('Severity:', det['severity'])
        print('Nearest Hospital ID:', det.get('nearest_hospital_id'))
        print('Nearest Hospital Object:', det.get('nearest_hospital'))

if __name__ == '__main__':
    check()
