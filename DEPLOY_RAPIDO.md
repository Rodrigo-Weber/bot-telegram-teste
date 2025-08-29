# 🚀 Deploy Rápido no Easypanel

## ⚡ Passos para Deploy em 5 Minutos

### 1️⃣ Preparar Arquivos
- ✅ Todos os arquivos já estão prontos na pasta
- ✅ O bot está configurado e funcional

### 2️⃣ Configurar Variáveis (2 min)
1. Copie `env.example` para `.env`
2. Preencha com seus dados reais:
   - **TELEGRAM_TOKEN** (do @BotFather)
   - **DB_PASSWORD** (senha para MySQL)
   - **MERCADO_PAGO_ACCESS_TOKEN** (já configurado)
   - **OWNER_USER_ID** (já configurado)

### 3️⃣ Deploy no Easypanel (3 min)

#### Opção A: Via Git (Recomendado)
```bash
git init
git add .
git commit -m "Bot Financeiro v1.0"
git remote add origin SEU_REPO_GIT
git push -u origin main
```
- No Easypanel: Novo Projeto → Git Repository → Cole URL

#### Opção B: Via Upload
- Compacte todos os arquivos (exceto `.env`) em ZIP
- No Easypanel: Novo Projeto → Upload Files → Faça upload

### 4️⃣ Configurar no Easypanel
- Cole todas as variáveis do `.env` nas variáveis de ambiente
- Deploy!

### 5️⃣ Testar
- Envie `/inicio` para o bot no Telegram
- ✅ Pronto! Bot funcionando!

---

## 🔧 Comandos Úteis

```bash
# Ver logs
docker logs finance-bot

# Parar serviços
docker-compose down

# Reiniciar
docker-compose restart

# Status
docker-compose ps
```

---

## 📱 Funcionalidades do Bot

- 💰 Controle de despesas e receitas
- 🎙️ Registro por voz com IA
- 💳 Sistema de pagamento PIX
- 📊 Relatórios diários/semanais/mensais
- 🏷️ Categorização automática
- 🔒 Sistema de assinatura

---

## 🆘 Suporte Rápido

**Problema:** Bot não responde
**Solução:** Verificar TELEGRAM_TOKEN e logs

**Problema:** Erro de banco
**Solução:** Verificar DB_PASSWORD e conexão MySQL

**Problema:** Erro de voz
**Solução:** Verificar FFmpeg no container

---

**🎯 Dica:** Use o arquivo `easypanel.json` para configuração automática!
