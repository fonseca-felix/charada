import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, current_app

def gerar_token(usuario):
    """Gera token JWT para o usuário"""
    secret_key = current_app.config.get("SECRET_KEY")
    if not secret_key:
        secret_key = "feliz-namorado-da-majuzinha"
    
    payload = {
        "usuario": usuario,
        "perfil": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")

def token_obrigatorio(func):
    """Decorator para proteger rotas que exigem token"""
    @wraps(func)
    def verificar_token(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return jsonify({"erro": "Token não fornecido"}), 401
        
        if not auth_header.startswith("Bearer "):
            return jsonify({"erro": "Formato de token inválido. Use Bearer token"}), 401
        
        token = auth_header.split(" ")[1]
        
        try:
            secret_key = current_app.config.get("SECRET_KEY", "feliz-namorado-da-majuzinha")
            dados_token = jwt.decode(token, secret_key, algorithms=["HS256"])
            request.usuario_logado = dados_token
        except jwt.ExpiredSignatureError:
            return jsonify({"erro": "Token expirado"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"erro": f"Token inválido: {str(e)}"}), 401
        
        return func(*args, **kwargs)
    
    return verificar_token