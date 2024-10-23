import requests

# URL da API com query parameters
url = 'http://192.168.2.108:3001/Perguntas?pergunt01 - Sejam Bem Vindos'

response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print(data[0])
else:
    print(f'Error: {response.status_code}')
