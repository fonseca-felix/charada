import os
import random
import firebase_admin
from flask import Flask, jsonify, request
from firebase_admin import credentials, firestore
import json
from datetime import datetime, timezone
from flask_cors import CORS
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (local)
load_dotenv()

# Importa o módulo de autenticação
from auth import gerar_token, token_obrigatorio

# 1. Configuração do Firebase (Híbrida: Local ou Nuvem)
db = None
try:
    if not firebase_admin._apps:
        # Tenta carregar da variável de ambiente da Vercel primeiro
        firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS")
        
        if firebase_creds_json:
            # Converte a string JSON da Vercel em um dicionário
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase conectado via Variável de Ambiente (Vercel)!")
        elif os.path.exists("firebase.json"):
            # Caso esteja rodando localmente com o arquivo físico
            cred = credentials.Certificate("firebase.json")
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase conectado via arquivo local (firebase.json)!")
        else:
            print("ERRO: Nenhuma credencial do Firebase encontrada (Variável ou Arquivo)!")
            
except Exception as e:
    print(f"ERRO ao conectar ao Firebase: {e}")
    db = None

app = Flask(__name__)
# Configuração de Segurança - Usa a variável 'SECRET_KEY' da Vercel ou o valor do seu .env [cite: 1]
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-jwt-aqui-mude-em-producao')
CORS(app, origins="*")

# Configuração de admin extraída das variáveis de ambiente [cite: 1]
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
        
        if not username or not password:
            return jsonify({'error': 'Username e password são obrigatórios'}), 400
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            token = gerar_token(username)
            return jsonify({
                'message': 'Login realizado com sucesso',
                'token': token,
                'token_type': 'Bearer',
                'usuario': username
            }), 200
        else:
            return jsonify({'error': 'Usuário ou senha inválidos!'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- ENDPOINTS PÚBLICOS ---

@app.route('/')
def root():
    return jsonify({
        'api': 'charadas',
        'version': '1.2',
        'autor': 'feliz',
        'status': 'online',
        'auth': 'JWT'
    }), 200

@app.route('/charadas', methods=['GET'])
def get_charadas():
    try:
        if db is None:
            return jsonify({'error': 'Firebase não disponível'}), 500
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
        if db is None:
            return jsonify({'error': 'Firebase não disponível'}), 500
        lista = list(db.collection('charadas').stream())
        if not lista:
            return jsonify({'error': 'Nenhuma charada encontrada'}), 404
        escolhida = random.choice(lista)
        dados = escolhida.to_dict()
        dados['id'] = escolhida.id
        return jsonify(dados), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/<id>', methods=['GET'])
def get_charada_by_id(id):
    try:
        if db is None:
            return jsonify({'error': 'Firebase não disponível'}), 500
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
        if db is None:
            return jsonify({'error': 'Firebase não disponível'}), 500
        
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
        if db is None:
            return jsonify({'error': 'Firebase não disponível'}), 500
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
        return jsonify({'message': f'{len(charadas_adicionadas)} adicionadas com sucesso', 'adicionadas': len(charadas_adicionadas)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/charadas/<id>', methods=['DELETE'])
@token_obrigatorio
def delete_charada(id):
    try:
        if db is None:
            return jsonify({'error': 'Firebase não disponível'}), 500
        doc_ref = db.collection('charadas').document(id)
        if not doc_ref.get().exists:
            return jsonify({'error': 'Documento não existe'}), 404
        doc_ref.delete()
        return jsonify({'message': f'Charada {id} removida com sucesso'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'api': 'charadas',
        'status': 'online',
        'firebase': "conectado" if db else "erro",
        'version': '1.2'
    }), 200

# Exporta o app para a Vercel
app.debug = True

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)