@echo off
echo Configurando variaveis de ambiente para o Bot Financeiro...
echo.

REM Copiar o arquivo de exemplo para .env
copy "env_configurado.txt" ".env"

if %errorlevel% equ 0 (
    echo ✅ Arquivo .env criado com sucesso!
    echo.
    echo 📋 Variaveis configuradas:
    echo    - TELEGRAM_TOKEN: Configurado
    echo    - DB_PASSWORD: FinanceBot2024!
    echo    - MERCADO_PAGO_ACCESS_TOKEN: Configurado
    echo    - OWNER_USER_ID: 7287573737
    echo.
    echo 🚀 Agora voce pode fazer o deploy no Easypanel!
    echo.
    echo 📝 Para verificar, abra o arquivo .env
    notepad .env
) else (
    echo ❌ Erro ao criar arquivo .env
    echo.
    echo 💡 Solucao manual:
    echo    1. Copie o conteudo de env_configurado.txt
    echo    2. Crie um arquivo chamado .env
    echo    3. Cole o conteudo
)

pause
