from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import os

load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)

VOXA_BASE      = 'https://mock.voxa.work/'
RECOGNITA_BASE = 'https://api.recognita.com.br/mock'

SUPABASE_URL      = os.getenv('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/config')
def get_config():
    return jsonify({
        'supabase_url':      SUPABASE_URL,
        'supabase_anon_key': SUPABASE_ANON_KEY
    })


@app.route('/api/links')
def get_links():
    provider   = request.args.get('provider', 'voxa')
    assessment = request.args.get('assessment', '')
    amount     = request.args.get('amount', '3')
    lang       = request.args.get('lang', '')

    try:
        if provider == 'recognita':
            key    = os.getenv('RECOGNITA_KEY')
            params = {'key': key, 'amount': amount}
            if lang:
                params['lang'] = lang
            resp = requests.get(RECOGNITA_BASE, params=params, timeout=15)
        else:
            key    = os.getenv('VOXA_KEY')
            params = {'key': key, 'executionKey': assessment, 'isDeepLink': 'true', 'amount': amount}
            resp = requests.get(VOXA_BASE, params=params, timeout=15)

        resp.raise_for_status()
        data = resp.json()

        if data and isinstance(data[0], dict):
            links = [item['url'] for item in data]
        else:
            links = data

        return jsonify({'links': links})

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Timeout ao contatar a API'}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Erro na requisição: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500




@app.route('/api/log', methods=['POST'])
def log_event():
    data = request.get_json() or {}
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/panel_access_logs",
            headers={
                'apikey':          SUPABASE_ANON_KEY,
                'Authorization':   f'Bearer {SUPABASE_ANON_KEY}',
                'Content-Type':    'application/json',
                'Prefer':          'return=minimal'
            },
            json=data,
            timeout=5
        )
        if resp.ok:
            return jsonify({'ok': True})
        return jsonify({'error': resp.text}), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        @app.route('/api/log', methods=['POST'])
def log_event():
    data = request.get_json() or {}
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/panel_access_logs",
            headers={
                'apikey':        SUPABASE_ANON_KEY,
                'Authorization': f'Bearer {SUPABASE_ANON_KEY}',
                'Content-Type':  'application/json',
                'Prefer':        'return=minimal'
            },
            json=data,
            timeout=5
        )
        if resp.ok:
            return jsonify({'ok': True})
        return jsonify({'error': resp.text}), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
