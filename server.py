from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import os
import hmac
import hashlib
import time

load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)

VOXA_BASE      = 'https://mock.voxa.work/'
RECOGNITA_BASE = 'https://api.recognita.com.br/mock'

SUPABASE_URL      = os.getenv('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
SUPABASE_SVC_KEY  = os.getenv('SUPABASE_SERVICE_KEY', '')
HUB_SECRET        = os.getenv('HUB_SECRET', '')

# ── Hub token format (add to hub page) ────────────────────────────────────────
# import hmac, hashlib, time
# secret = HUB_SECRET  (same value from .env)
# email  = "usuario@empresa.com"
# ts     = str(int(time.time()))
# token  = hmac.new(secret.encode(), f"{email}:{ts}".encode(), hashlib.sha256).hexdigest()
# url    = f"https://seu-app.com?hub_token={token}&hub_email={email}&hub_ts={ts}"
# ──────────────────────────────────────────────────────────────────────────────


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/config')
def get_config():
    return jsonify({
        'supabase_url':      SUPABASE_URL,
        'supabase_anon_key': SUPABASE_ANON_KEY
    })


@app.route('/api/auth/hub-login', methods=['POST'])
def hub_login():
    if not HUB_SECRET or not SUPABASE_URL or not SUPABASE_SVC_KEY:
        return jsonify({'error': 'Autenticação não configurada'}), 500

    body  = request.get_json(silent=True) or {}
    token = body.get('token', '')
    email = body.get('email', '')
    ts    = body.get('ts', '')

    try:
        if abs(time.time() - int(ts)) > 600:
            return jsonify({'error': 'Token expirado'}), 401
    except (ValueError, TypeError):
        return jsonify({'error': 'Token inválido'}), 401

    expected = hmac.new(
        HUB_SECRET.encode(),
        f'{email}:{ts}'.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(token, expected):
        return jsonify({'error': 'Token inválido'}), 401

    redirect_to = request.host_url.rstrip('/')
    headers = {
        'apikey':        SUPABASE_SVC_KEY,
        'Authorization': f'Bearer {SUPABASE_SVC_KEY}',
        'Content-Type':  'application/json'
    }
    payload = {'type': 'magiclink', 'email': email, 'redirect_to': redirect_to}

    try:
        r = requests.post(
            f'{SUPABASE_URL}/auth/v1/admin/generate_link',
            json=payload, headers=headers, timeout=10
        )
        r.raise_for_status()
        magic_link = r.json().get('action_link')
        return jsonify({'magic_link': magic_link})
    except Exception as e:
        return jsonify({'error': f'Erro ao gerar link: {str(e)}'}), 500


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


if __name__ == '__main__':
    app.run(port=5000, debug=True)
