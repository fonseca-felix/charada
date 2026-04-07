import os
import random
import json
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger

# 
# Importação condicional do Firebase
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Firebase Admin não disponível")

# Importação condicional do auth
try:
    from auth import gerar_token, token_obrigatorio
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    print("Auth não disponível")
    
    # Placeholders
    def gerar_token(usuario):
        return "token_temp"
    def token_obrigatorio(func):
        return func

app = Flask(__name__)

# Versão do OpenAPI
app.config['SWAGGER'] = {
    'openapi': '3.0.3'
}

# Chamar o OpenAPI para o codigo
swagger = Swagger(app, template_file="openapi.yaml")

# Configurações básicas
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY')
CORS(app)

# Configurações do admin
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# Inicialização do Firebase
db = None
if FIREBASE_AVAILABLE and not firebase_admin._apps:
    try:
        firebase_creds_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        
        if firebase_creds_json:
            # Usa credencial da variável de ambiente
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase conectado via env")
        elif os.path.exists("firebase.json"):
            # Fallback para local
            cred = credentials.Certificate("firebase.json")
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase conectado via arquivo")
        else:
            print("Firebase: sem credenciais")
    except Exception as e:
        print(f"Erro Firebase: {e}")

# Rota raiz
@app.route('/')
def root():
    return jsonify({
        'api': 'Charadas API',
        'status': 'online',
        'firebase': 'conectado' if db else 'offline',
        'auth': 'ativo' if AUTH_AVAILABLE else 'simplificado',
        'version': '2.0'
    })

# Status detalhado
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'firebase': db is not None,
        'environment': 'vercel' if os.environ.get('VERCEL') else 'local'
    })

# Login
@app.route('/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
        
        username = dados.get('username')
        password = dados.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            token = gerar_token(username)
            return jsonify({
                'token': token,
                'usuario': username,
                'message': 'Login realizado com sucesso'
            }), 200
        
        return jsonify({'erro': 'Credenciais inválidas'}), 401
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Listar todas charadas
@app.route('/charadas', methods=['GET'])
def get_charadas():
    if not db:
        return jsonify({'erro': 'Banco de dados não disponível'}), 503
    
    try:
        charadas = []
        docs = db.collection('charadas').stream()
        for doc in docs:
            item = doc.to_dict()
            item['id'] = doc.id
            charadas.append(item)
        return jsonify(charadas), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Charada aleatória
@app.route('/charadas/aleatoria', methods=['GET'])
def get_charada_aleatoria():
    if not db:
        return jsonify({'erro': 'Banco de dados não disponível'}), 503
    
    try:
        docs = list(db.collection('charadas').stream())
        if not docs:
            return jsonify({'erro': 'Nenhuma charada encontrada'}), 404
        
        escolhida = random.choice(docs)
        item = escolhida.to_dict()
        item['id'] = escolhida.id
        return jsonify(item), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Buscar por ID
@app.route('/charadas/<id>', methods=['GET'])
def get_charada_by_id(id):
    if not db:
        return jsonify({'erro': 'Banco de dados não disponível'}), 503
    
    try:
        doc = db.collection('charadas').document(id).get()
        if doc.exists:
            item = doc.to_dict()
            item['id'] = doc.id
            return jsonify(item), 200
        return jsonify({'erro': 'Charada não encontrada'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Criar charada (protegido)
@app.route('/charadas', methods=['POST'])
@token_obrigatorio
def create_charada():
    if not db:
        return jsonify({'erro': 'Banco de dados não disponível'}), 503
    
    try:
        dados = request.get_json()
        
        # ID sequencial
        cont_ref = db.collection('contador').document('controle_id')
        doc = cont_ref.get()
        prox_id = (doc.to_dict().get('ultimo_id', 0) if doc.exists else 0) + 1
        
        dados['id'] = prox_id
        dados['criado_em'] = datetime.now(timezone.utc).isoformat()
        
        db.collection('charadas').document(str(prox_id)).set(dados)
        cont_ref.set({'ultimo_id': prox_id})
        
        return jsonify({'id': prox_id, 'message': 'Charada criada com sucesso'}), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Deletar charada (protegido)
@app.route('/charadas/<id>', methods=['DELETE'])
@token_obrigatorio
def delete_charada(id):
    if not db:
        return jsonify({'erro': 'Banco de dados não disponível'}), 503
    
    try:
        db.collection('charadas').document(id).delete()
        return jsonify({'message': f'Charada {id} removida'}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Para rodar localmente
if __name__ == '__main__':
    app.run(debug=True, port=5000)