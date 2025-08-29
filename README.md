# 🤖 Bot Financeiro para Telegram

Bot inteligente para controle financeiro pessoal com suporte a reconhecimento de voz e integração com Mercado Pago.

## 🚀 Deploy no Easypanel

### 1. Preparação dos Arquivos

Certifique-se de que todos os arquivos estão na pasta do projeto:
- `finance_bot.py` - Código principal do bot
- `requirements.txt` - Dependências Python
- `Dockerfile` - Configuração do container
- `docker-compose.yml` - Orquestração dos serviços
- `init.sql` - Estrutura do banco de dados
- `env.example` - Exemplo de variáveis de ambiente

### 2. Configuração das Variáveis de Ambiente

1. Copie o arquivo `env.example` para `.env`
2. Preencha todas as variáveis com seus dados reais:

```bash
# Token do Bot do Telegram (obtido via @BotFather)
TELEGRAM_TOKEN=8403356080:AAHXS8gsXd6jYdSra_1uiHz0sPJZfvCnulk

# Configurações do Banco de Dados
DB_HOST=mysql
DB_DATABASE=telegram_financas_bot
DB_USER=root
DB_PASSWORD=sua_senha_segura_aqui

# Configurações do Mercado Pago
MERCADO_PAGO_ACCESS_TOKEN=APP_USR-759602526921954-082507-0fc45feda769868688acb72646b7a6d8-302693772
PAYER_EMAIL=rodrigo.novais@live.com
RECIPIENT_DISPLAY_NAME=Rodrigo Weber Silva Novaes
OWNER_USER_ID=7287573737

# Dados de Suporte
SUPPORT_NAME=Rodrigo Weber
SUPPORT_EMAIL=rodrigo.novais@live.com
SUPPORT_PHONE=+55 (71) 98381-9052
```

### 3. Deploy no Easypanel

#### Opção A: Deploy via Git (Recomendado)

1. **Faça commit dos arquivos para um repositório Git:**
   ```bash
   git init
   git add .
   git commit -m "Primeira versão do bot financeiro"
   git remote add origin SEU_REPOSITORIO_GIT
   git push -u origin main
   ```

2. **No Easypanel:**
   - Crie um novo projeto
   - Selecione "Git Repository"
   - Cole a URL do seu repositório
   - Configure as variáveis de ambiente
   - Deploy!

#### Opção B: Deploy via Upload de Arquivos

1. **Compacte todos os arquivos em um ZIP:**
   - Selecione todos os arquivos (exceto `.env`)
   - Crie um arquivo ZIP

2. **No Easypanel:**
   - Crie um novo projeto
   - Selecione "Upload Files"
   - Faça upload do ZIP
   - Configure as variáveis de ambiente
   - Deploy!

### 4. Configuração do Easypanel

#### Variáveis de Ambiente
Configure todas as variáveis listadas no arquivo `.env` no painel do Easypanel.

#### Portas
- **MySQL:** 3306 (interno)
- **Bot:** 8000 (se necessário para webhooks)

#### Volumes
- `mysql_data` - Para persistir dados do banco
- `./logs:/app/logs` - Para logs do bot

### 5. Verificação do Deploy

1. **Verifique os logs do container:**
   ```bash
   docker logs finance-bot
   ```

2. **Teste o bot no Telegram:**
   - Envie `/inicio` para o bot
   - Verifique se responde corretamente

3. **Verifique o banco de dados:**
   - Conecte ao MySQL
   - Verifique se as tabelas foram criadas

### 6. Comandos Disponíveis

- `/inicio` - Mensagem de boas-vindas
- `/entradas` - Registrar entrada de dinheiro
- `/despesas` - Registrar gastos
- `/saldo` - Ver saldo atual
- `/dia` - Relatório do dia
- `/semana` - Relatório da semana
- `/mes` - Relatório do mês
- `/pagamento` - Sistema de pagamento
- `/suporte` - Informações de suporte
- **Mensagem de voz** - Registro automático com IA

### 7. Solução de Problemas

#### Bot não responde
- Verifique se o token do Telegram está correto
- Confirme se o container está rodando
- Verifique os logs do bot

#### Erro de conexão com banco
- Verifique se o MySQL está rodando
- Confirme as credenciais do banco
- Verifique se o container do bot consegue acessar o MySQL

#### Erro de reconhecimento de voz
- Verifique se o FFmpeg está instalado
- Confirme se as bibliotecas de áudio estão funcionando

### 8. Manutenção

#### Backup do Banco
```bash
docker exec finance-bot-mysql mysqldump -u root -p telegram_financas_bot > backup.sql
```

#### Atualização do Bot
1. Faça as alterações no código
2. Commit e push para o Git
3. Redeploy no Easypanel

#### Monitoramento
- Configure alertas para falhas do container
- Monitore o uso de recursos
- Verifique logs regularmente

## 📞 Suporte

Para dúvidas ou problemas:
- **Nome:** Rodrigo Weber
- **Email:** rodrigo.novais@live.com
- **Telefone:** +55 (71) 98381-9052

---

**⚠️ Importante:** Nunca compartilhe suas chaves de API ou tokens em repositórios públicos!
