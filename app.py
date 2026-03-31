import os
import random
import firebase_admin
import json
from flask import Flask, jsonify, request
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
from flask_cors import CORS
from dotenv import load_dotenv

# Carrega variáveis de ambiente de um arquivo .env (apenas para desenvolvimento local)
load_dotenv()

# Importa o módulo de autenticação
from auth import gerar_token, token_obrigatorio

app = Flask(__name__)

# Configuração de Segurança via Variáveis de Ambiente 
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-jwt-aqui-mude-em-producao')
CORS(app, origins="*")

# --- CONFIGURAÇÃO DO FIREBASE ADAPTADA PARA NUVEM ---
db = None
try:
    # Em ambientes serverless como a Vercel, verificamos se o app já existe
    if not firebase_admin._apps:
        firebase_creds_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        
        if firebase_creds_json:
            # Converte a string da variável de ambiente para dicionário JSON
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase conectado via Variável de Ambiente!")
        elif os.path.exists("firebase.json"):
            # Fallback para desenvolvimento local caso o arquivo exista
            cred = credentials.Certificate("firebase.json")
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase conectado via arquivo local!")
    else:
        db = firestore.client()
except Exception as e:
    print(f"ERRO ao conectar ao Firebase: {e}")

# Configurações de admin vindas do ambiente 
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# --- ENDPOINT DE LOGIN ---
@app.route('/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        username = dados.get('username')
        password = dados.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            token = gerar_token(username)
            return jsonify({
                'message': 'Login realizado com sucesso',
                'token': token,
                'token_type': 'Bearer',
                'usuario': username
            }), 200
        return jsonify({'error': 'Usuário ou senha inválidos!'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- ENDPOINTS PÚBLICOS ---
@app.route('/')
def root():
    return jsonify({
        'api': 'charadas',
        'version': '1.0',
        'autor': 'feliz',
        'status': 'online',
        'auth': 'JWT'
    }), 200

@app.route('/charadas', methods=['GET'])
def get_charadas():
    try:
        if db is None: return jsonify({'error': 'Firebase não disponível'}), 500
        charadas = []
        lista = db.collection('charadas').stream()
        for item in lista:
            dados = item.to_dict()
            dados['id'] = item.id
            charadas.append(dados)
        return jsonify(charadas), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/aleatoria', methods=['GET'])
def get_charadas_random():
    try:
        if db is None: return jsonify({'error': 'Firebase não disponível'}), 500
        lista = list(db.collection('charadas').stream())
        if not lista: return jsonify({'error': 'Nenhuma charada encontrada'}), 404
        escolhida = random.choice(lista)
        dados = escolhida.to_dict()
        dados['id'] = escolhida.id
        return jsonify(dados), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/<id>', methods=['GET'])
def get_charada_by_id(id):
    try:
        if db is None: return jsonify({'error': 'Firebase não disponível'}), 500
        doc_ref = db.collection('charadas').document(id)
        doc = doc_ref.get()
        if doc.exists:
            dados = doc.to_dict()
            dados['id'] = doc.id
            return jsonify(dados), 200
        return jsonify({'error': 'Charada não encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- ENDPOINTS PRIVADOS ---
@app.route('/charadas', methods=['POST'])
@token_obrigatorio
def create_charada():
    try:
        if db is None: return jsonify({'error': 'Firebase não disponível'}), 500
        nova_charada = request.get_json()
        if not nova_charada or 'pergunta' not in nova_charada or 'resposta' not in nova_charada:
            return jsonify({'error': 'Campos obrigatórios: pergunta e resposta'}), 400
        
        contador_ref = db.collection('contador').document('controle_id')
        contador_doc = contador_ref.get()
        ultimo_id = contador_doc.to_dict().get('ultimo_id', 0) if contador_doc.exists else 0
        
        novo_id = ultimo_id + 1
        nova_charada['id'] = novo_id
        nova_charada['criado_por'] = request.usuario_logado.get('usuario')
        nova_charada['criado_em'] = datetime.now(timezone.utc).isoformat()
        
        db.collection('charadas').document(str(novo_id)).set(nova_charada)
        contador_ref.set({'ultimo_id': novo_id})
        
        return jsonify({'id': novo_id, 'message': 'Criado com sucesso', 'charada': nova_charada}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/massivas', methods=['POST'])
@token_obrigatorio
def create_multiplas_charadas():
    try:
        if db is None: return jsonify({'error': 'Firebase não disponível'}), 500
        dados = request.get_json()
        if not dados or 'charadas' not in dados:
            return jsonify({'error': 'Campo obrigatório: charadas'}), 400
        
        charadas_lista = dados['charadas']
        contador_ref = db.collection('contador').document('controle_id')
        contador_doc = contador_ref.get()
        ultimo_id = contador_doc.to_dict().get('ultimo_id', 0) if contador_doc.exists else 0
        
        charadas_adicionadas = []
        for charada in charadas_lista:
            ultimo_id += 1
            charada_completa = {
                'id': ultimo_id,
                'pergunta': charada['pergunta'],
                'resposta': charada['resposta'],
                'criado_por': request.usuario_logado.get('usuario'),
                'criado_em': datetime.now(timezone.utc).isoformat()
            }
            db.collection('charadas').document(str(ultimo_id)).set(charada_completa)
            charadas_adicionadas.append({'id': ultimo_id, 'pergunta': charada['pergunta']})
        
        contador_ref.update({'ultimo_id': ultimo_id})
        return jsonify({'message': f'{len(charadas_adicionadas)} adicionadas', 'charadas_criadas': charadas_adicionadas}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/<id>', methods=['PATCH'])
@token_obrigatorio
def patch_charada(id):
    try:
        if db is None: return jsonify({'error': 'Firebase não disponível'}), 500
        dados_atualizar = request.get_json()
        doc_ref = db.collection('charadas').document(id)
        if not doc_ref.get().exists: return jsonify({'error': 'Não existe'}), 404
            
        dados_atualizar['atualizado_por'] = request.usuario_logado.get('usuario')
        dados_atualizar['atualizado_em'] = datetime.now(timezone.utc).isoformat()
        doc_ref.update(dados_atualizar)
        return jsonify({'message': 'Atualizado parcialmente'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/<id>', methods=['PUT'])
@token_obrigatorio
def update_charada(id):
    try:
        if db is None: return jsonify({'error': 'Firebase não disponível'}), 500
        dados_novos = request.get_json()
        doc_ref = db.collection('charadas').document(id)
        if not doc_ref.get().exists: return jsonify({'error': 'Não existe'}), 404
        
        dados_novos['id'] = int(id) if id.isdigit() else id
        dados_novos['atualizado_por'] = request.usuario_logado.get('usuario')
        dados_novos['atualizado_em'] = datetime.now(timezone.utc).isoformat()
        doc_ref.set(dados_novos)
        return jsonify({'message': 'Substituído com sucesso'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/<id>', methods=['DELETE'])
@token_obrigatorio
def delete_charada(id):
    try:
        if db is None: return jsonify({'error': 'Firebase não disponível'}), 500
        doc_ref = db.collection('charadas').document(id)
        if not doc_ref.get().exists: return jsonify({'error': 'Não existe'}), 404
        doc_ref.delete()
        return jsonify({'message': f'Charada {id} removida'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({'api': 'charadas', 'status': 'online', 'firebase': "conectado" if db else "erro"}), 200

# Necessário para a Vercel exportar a aplicação
app.debug = True