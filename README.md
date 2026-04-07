<div align="center">
  <img src="https://img.icons8.com/color/96/000000/quiz--v1.png" alt="Logo" width="80">
  <h1>🤔 API de Charadas</h1>
  <p><strong>Uma API RESTful divertida para gerenciar e compartilhar charadas</strong></p>
  
  <a href="https://charada-orpin.vercel.app">
    <img src="https://img.shields.io/badge/API-Online-00C853?style=for-the-badge&logo=vercel&logoColor=white" alt="Status Online">
  </a>
  <img src="https://img.shields.io/badge/Version-2.0-blue?style=for-the-badge" alt="Version 2.0">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License MIT">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-2.3.3-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/Firebase-6.4.0-FFCA28?style=for-the-badge&logo=firebase&logoColor=black" alt="Firebase">
</div>

---

## 📖 Sobre o Projeto

Esta é uma API backend desenvolvida para gerenciar um banco de dados de charadas. Com ela, você pode listar, buscar, criar e deletar charadas de forma simples e eficiente. O projeto inclui autenticação JWT para operações administrativas e armazenamento em nuvem via Firebase Firestore.

> 🎯 **Disponível em:** [https://charada-orpin.vercel.app](https://charada-orpin.vercel.app)

### Características Principais

- ✅ **Rápida e Leve** - Construída com Flask, uma das frameworks Python mais leves
- ✅ **Escalável** - Utiliza Firebase Firestore como banco de dados NoSQL
- ✅ **Segura** - Autenticação JWT para rotas administrativas
- ✅ **Documentada** - Endpoints claros e fáceis de usar
- ✅ **Hospedada na Vercel** - Performance global e alta disponibilidade

---

## ✨ Funcionalidades

| Funcionalidade | Descrição | Autenticação | Método HTTP |
|----------------|-----------|--------------|--------------|
| 📋 **Listar todas** | Retorna todas as charadas cadastradas | ❌ Não | GET |
| 🎲 **Charada aleatória** | Retorna uma charada aleatória do banco | ❌ Não | GET |
| 🔍 **Buscar por ID** | Encontra uma charada específica pelo ID | ❌ Não | GET |
| ➕ **Criar charada** | Adiciona uma nova charada ao banco | ✅ Sim (Admin) | POST |
| 🗑️ **Deletar charada** | Remove uma charada existente | ✅ Sim (Admin) | DELETE |
| 🔐 **Login** | Autenticação para obter token JWT | ❌ Não | POST |
| 🏠 **Status** | Verifica o status da API | ❌ Não | GET |

---
