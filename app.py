import os
import random
import firebase_admin
from flask import Flask, jsonify, request
from firebase_admin import credentials, firestore
import json
from datetime import datetime, timezone
from flask_cors import CORS
from dotenv import load_dotenv

# Carrega variáveis do .env para testes locais
load_dotenv()

# Importa o módulo de autenticação (auth.py deve estar na mesma pasta)
try:
    from auth import gerar_token, token_obrigatorio
except ImportError as e:
    print(f"Erro ao importar auth: {e}")
    # Define funções placeholder para evitar crash
    def gerar_token(usuario):
        return "token_placeholder"
    def token_obrigatorio(func):
        return func

# --- 1. CONFIGURAÇÃO DO FIREBASE (NUVEM + LOCAL) ---
db = None
try:
    if not firebase_admin._apps:
        # Tenta carregar da variável de ambiente que você configurou na Vercel
        firebase_creds_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        
        if firebase_creds_json:
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase: Conectado via FIREBASE_SERVICE_ACCOUNT")
        elif os.path.exists("firebase.json"):
            # Fallback para teste local
            cred = credentials.Certificate("firebase.json")
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase: Conectado via arquivo local")
        else:
            print("Firebase: Nenhuma credencial encontrada")
            
except Exception as e:
    print(f"ERRO de conexão Firebase: {e}")

app = Flask(__name__)

# --- 2. CONFIGURAÇÃO DE SEGURANÇA ---
# Usa a sua frase: 'feliz-namorado-da-majuzinha'
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', 'feliz-namorado-da-majuzinha')
CORS(app)  # Simplificado

# Admin Creds (Vercel Variables)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# --- 3. ROTAS DE AUTENTICAÇÃO ---

@app.route('/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        if not dados: 
            return jsonify({'error': 'Sem dados'}), 400
        
        username = dados.get('username')
        password = dados.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            token = gerar_token(username)
            return jsonify({
                'message': 'Login realizado',
                'token': token,
                'token_type': 'Bearer',
                'usuario': username
            }), 200
        return jsonify({'error': 'Usuário ou senha inválidos!'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- 4. ROTAS PÚBLICAS (VISUALIZAÇÃO) ---

@app.route('/')
def root():
    return jsonify({
        'api': 'charadas',
        'status': 'online',
        'version': '1.2',
        'mensagem': 'Bem-vindo à API de Charadas!'
    }), 200

@app.route('/charadas', methods=['GET'])
def get_charadas():
    try:
        if not db:
            return jsonify({'error': 'DB Offline', 'message': 'Firebase não configurado'}), 500
        charadas = []
        docs = db.collection('charadas').stream()
        for doc in docs:
            item = doc.to_dict()
            item['id'] = doc.id
            charadas.append(item)
        return jsonify(charadas), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/aleatoria', methods=['GET'])
def get_charadas_random():
    try:
        if not db:
            return jsonify({'error': 'DB Offline'}), 500
        docs = list(db.collection('charadas').stream())
        if not docs:
            return jsonify({'error': 'Vazio'}), 404
        escolhida = random.choice(docs)
        item = escolhida.to_dict()
        item['id'] = escolhida.id
        return jsonify(item), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/<id>', methods=['GET'])
def get_charada_by_id(id):
    try:
        if not db:
            return jsonify({'error': 'DB Offline'}), 500
        doc = db.collection('charadas').document(id).get()
        if doc.exists:
            item = doc.to_dict()
            item['id'] = doc.id
            return jsonify(item), 200
        return jsonify({'error': 'Não encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- 5. ROTAS PRIVADAS (CRIAÇÃO E EDIÇÃO - REQUER TOKEN) ---

@app.route('/charadas', methods=['POST'])
@token_obrigatorio
def create_charada():
    try:
        if not db:
            return jsonify({'error': 'DB Offline'}), 500
        dados = request.get_json()
        
        # Lógica de ID Sequencial
        cont_ref = db.collection('contador').document('controle_id')
        doc = cont_ref.get()
        prox_id = (doc.to_dict().get('ultimo_id', 0) if doc.exists else 0) + 1
        
        dados['id'] = prox_id
        dados['criado_em'] = datetime.now(timezone.utc).isoformat()
        
        db.collection('charadas').document(str(prox_id)).set(dados)
        cont_ref.set({'ultimo_id': prox_id})
        
        return jsonify({'id': prox_id, 'message': 'Criada com sucesso'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/massivas', methods=['POST'])
@token_obrigatorio
def create_multiplas_charadas():
    try:
        if not db:
            return jsonify({'error': 'DB Offline'}), 500
        lista = request.get_json().get('charadas', [])
        
        cont_ref = db.collection('contador').document('controle_id')
        ultimo_id = cont_ref.get().to_dict().get('ultimo_id', 0)
        
        for item in lista:
            ultimo_id += 1
            item['id'] = ultimo_id
            db.collection('charadas').document(str(ultimo_id)).set(item)
            
        cont_ref.update({'ultimo_id': ultimo_id})
        return jsonify({'message': f'{len(lista)} charadas adicionadas'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/<id>', methods=['DELETE'])
@token_obrigatorio
def delete_charada(id):
    try:
        if not db:
            return jsonify({'error': 'DB Offline'}), 500
        db.collection('charadas').document(id).delete()
        return jsonify({'message': f'Charada {id} removida'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'online',
        'firebase': 'conectado' if db else 'erro',
        'ambiente': 'producao' if os.environ.get("VERCEL") else 'local'
    }), 200

# Para desenvolvimento local
if __name__ == '__main__':
    app.run(debug=True)