import sys
sys.path.insert(0, 'api')
from app import app

print('Routes registered:')
for rule in app.url_map.iter_rules():
    print(f'{rule.rule} -> {rule.endpoint}')

print('\nTesting health endpoint...')
with app.test_client() as client:
    response = client.get('/health')
    print(f'Status: {response.status_code}')
    print(f'Response: {response.get_json()}')

print('\nTesting analyze endpoint...')
with app.test_client() as client:
    response = client.get('/analyze?url=https://example.com')
    print(f'Status: {response.status_code}')
    print(f'Response: {response.get_json()}')

print('\nTesting llm-health endpoint...')
with app.test_client() as client:
    response = client.get('/llm-health')
    print(f'Status: {response.status_code}')
    print(f'Response: {response.get_json()}')
