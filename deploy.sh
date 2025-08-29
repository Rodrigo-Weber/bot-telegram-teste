#!/bin/bash

echo "🚀 Iniciando deploy do Bot Financeiro..."

# Verificar se o Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Por favor, instale o Docker primeiro."
    exit 1
fi

# Verificar se o Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado. Por favor, instale o Docker Compose primeiro."
    exit 1
fi

# Verificar se o arquivo .env existe
if [ ! -f .env ]; then
    echo "⚠️  Arquivo .env não encontrado. Copiando de env.example..."
    cp env.example .env
    echo "📝 Por favor, edite o arquivo .env com suas configurações reais antes de continuar."
    echo "🔑 Configure especialmente:"
    echo "   - TELEGRAM_TOKEN"
    echo "   - DB_PASSWORD"
    echo "   - MERCADO_PAGO_ACCESS_TOKEN"
    echo "   - OWNER_USER_ID"
    echo ""
    echo "Depois de configurar, execute este script novamente."
    exit 1
fi

echo "✅ Arquivo .env encontrado"

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose down

# Remover imagens antigas
echo "🧹 Removendo imagens antigas..."
docker-compose down --rmi all

# Construir e iniciar
echo "🔨 Construindo e iniciando containers..."
docker-compose up --build -d

# Aguardar inicialização
echo "⏳ Aguardando inicialização dos serviços..."
sleep 30

# Verificar status
echo "📊 Verificando status dos containers..."
docker-compose ps

# Verificar logs do bot
echo "📝 Últimos logs do bot:"
docker-compose logs --tail=20 finance-bot

echo ""
echo "🎉 Deploy concluído!"
echo ""
echo "📱 Para testar o bot:"
echo "   1. Envie /inicio para o bot no Telegram"
echo "   2. Verifique se responde corretamente"
echo ""
echo "🔍 Para ver logs em tempo real:"
echo "   docker-compose logs -f finance-bot"
echo ""
echo "🛑 Para parar os serviços:"
echo "   docker-compose down"
