import logging
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import qrcode
import io
import mercadopago
import base64
import uuid
import os
import re
import json
import requests

# --- BIBLIOTECAS PARA TRANSCRIÇÃO DE ÁUDIO ---
import speech_recognition as sr
from pydub import AudioSegment

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

# --- CONFIGURAÇÕES ---
# Substitua com o seu Token do BotFather
TELEGRAM_TOKEN = '8403356080:AAHXS8gsXd6jYdSra_1uiHz0sPJZfvCnulk' 

# Configurações do seu banco de dados MySQL local
DB_CONFIG = {
    'host': 'localhost',
    'database': 'telegram_financas_bot',
    'user': 'root', # Geralmente 'root' em ambiente local
    'password': 'root'
}

# --- DADOS PARA GERAÇÃO DO PIX (IMPORTANTE: PREENCHA COM SEUS DADOS) ---
MERCADO_PAGO_ACCESS_TOKEN = 'APP_USR-759602526921954-082507-0fc45feda769868688acb72646b7a6d8-302693772'
PAYER_EMAIL = "rodrigo.novais@live.com"
RECIPIENT_DISPLAY_NAME = "Rodrigo Weber Silva Novaes"
OWNER_USER_ID = 7287573737 # SUBSTITUA PELO SEU USER ID

# --- DADOS DE SUPORTE ---
SUPPORT_NAME = "Rodrigo Weber"
SUPPORT_EMAIL = "rodrigo.novais@live.com"
SUPPORT_PHONE = "+55 (71) 98381-9052"

# --- CONFIGURAÇÕES DE PAGAMENTO E CUPONS ---
BASE_PRICE = 15.00
COUPONS = {
    "OFF5": {"discount_value": 5.00, "type": "value"},
    "OFF7": {"free_days": 7, "type": "free_days"}
}
# Habilita o logging para depuração
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- FUNÇÕES DO BANCO DE DADOS ---

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        logger.error(f"Erro ao conectar ao MySQL: {e}")
        return None

def get_category_id_by_name(name="Mensalidade"):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT category_id FROM categories WHERE name = %s", (name,))
            category = cursor.fetchone()
            if category:
                return category['category_id']
            else:
                 cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
                 conn.commit()
                 return cursor.lastrowid
        except Error as e:
            logger.error(f"Erro ao buscar categoria '{name}': {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    return None

def get_categories_from_db():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT category_id, name FROM categories ORDER BY name ASC")
            categories = cursor.fetchall()
            return categories
        except Error as e:
            logger.error(f"Erro ao buscar categorias: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    return []

def save_user(user):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user.id,))
            if cursor.fetchone() is None:
                cursor.execute(
                    "INSERT INTO users (user_id, first_name, username) VALUES (%s, %s, %s)",
                    (user.id, user.first_name, user.username)
                )
                conn.commit()
        except Error as e:
            logger.error(f"Erro ao salvar usuário: {e}")
        finally:
            cursor.close()
            conn.close()

def save_transaction(user_id, trans_type, amount, description, category_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            sql = "INSERT INTO transactions (user_id, type, amount, description, category_id) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (user_id, trans_type, amount, description, category_id))
            conn.commit()
            return True
        except Error as e:
            logger.error(f"Erro ao salvar transação: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

# --- FUNÇÕES DE BANCO DE DADOS PARA MENSALIDADES ---
def save_pending_mensalidade(user_id, payment_id, valor):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            sql = "INSERT INTO mensalidades (user_id, payment_id, valor, status) VALUES (%s, %s, %s, 'pendente')"
            cursor.execute(sql, (user_id, payment_id, valor))
            conn.commit()
        except Error as e:
            logger.error(f"Erro ao salvar mensalidade pendente: {e}")
        finally:
            cursor.close()
            conn.close()

def grant_free_days(user_id, days, coupon_code):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            payment_id = f"CUPOM-{coupon_code}-{uuid.uuid4()}"
            sql = "INSERT INTO mensalidades (user_id, payment_id, valor, status, data_pagamento, dias_validade) VALUES (%s, %s, 0.00, 'pago', CURRENT_TIMESTAMP, %s)"
            cursor.execute(sql, (user_id, payment_id, days))
            conn.commit()
        except Error as e:
            logger.error(f"Erro ao conceder dias grátis: {e}")
        finally:
            cursor.close()
            conn.close()

def update_mensalidade_status(payment_id, new_status):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            if new_status == 'pago':
                sql = "UPDATE mensalidades SET status = %s, data_pagamento = CURRENT_TIMESTAMP WHERE payment_id = %s"
            else:
                sql = "UPDATE mensalidades SET status = %s WHERE payment_id = %s"
            cursor.execute(sql, (new_status, payment_id))
            conn.commit()
        except Error as e:
            logger.error(f"Erro ao atualizar status da mensalidade: {e}")
        finally:
            cursor.close()
            conn.close()

def get_active_subscription_end_date(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "SELECT data_pagamento, dias_validade FROM mensalidades WHERE user_id = %s AND status = 'pago' ORDER BY data_pagamento DESC LIMIT 1"
            cursor.execute(sql, (user_id,))
            latest_payment = cursor.fetchone()
            if latest_payment:
                payment_date = latest_payment['data_pagamento']
                valid_days = latest_payment['dias_validade']
                expiration_date = payment_date + timedelta(days=valid_days)
                if expiration_date > datetime.now():
                    return expiration_date
        except Error as e:
            logger.error(f"Erro ao buscar data da assinatura: {e}")
        finally:
            cursor.close()
            conn.close()
    return None

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if user_id == OWNER_USER_ID:
        return True
    if get_active_subscription_end_date(user_id):
        return True
    await update.message.reply_text(
        "❌ *Acesso Negado!*\n\nVocê precisa de uma assinatura ativa para usar este comando. Por favor, realize o pagamento usando o comando `/pagamento`.",
        parse_mode='Markdown'
    )
    return False

# --- FUNÇÃO DE INTERPRETAÇÃO DE TEXTO COM IA LOCAL (OLLAMA) ---

def interpretar_texto_com_ollama(texto: str, model: str = "gemma:2b") -> dict:
    """
    Usa um modelo do Ollama rodando localmente para extrair dados financeiros de um texto.
    """
    url = "http://localhost:11434/api/generate"

    prompt = f"""
    Sua tarefa é extrair informações financeiras de um texto. Retorne a resposta EXCLUSIVAMENTE em formato JSON, com as chaves: "type", "amount", "description", "category_name".
    Se uma informação não estiver clara, retorne o valor como null.

    Exemplos:
    Texto: "gastei 25 reais e 50 centavos no pão hoje de manhã na categoria padaria"
    JSON: {{"type": "despesa", "amount": 25.50, "description": "Pão hoje de manhã", "category_name": "Padaria"}}

    Texto: "recebi 1200 do freela de design"
    JSON: {{"type": "entrada", "amount": 1200.00, "description": "Freela de design", "category_name": null}}

    Texto: "supermercado deu 150 essa semana, foi na categoria compras"
    JSON: {{"type": "despesa", "amount": 150.00, "description": "Supermercado essa semana", "category_name": "Compras"}}
    
    Agora, analise o seguinte texto:
    Texto: "{texto}"
    JSON:
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        response_json = response.json()
        dados = json.loads(response_json['response'])
        return dados

    except requests.exceptions.ConnectionError:
        logger.error("Erro de conexão com o Ollama. Verifique se o Ollama está rodando.")
        return {"error": "connection_failed"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição para o Ollama: {e}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar o JSON da resposta do Ollama: {e}")
        return {}
    except Exception as e:
        logger.error(f"Erro inesperado na função do Ollama: {e}")
        return {}

# --- HANDLER PRINCIPAL PARA MENSAGENS DE VOZ ---

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_subscription(update, context):
        return

    user_id = update.effective_user.id
    file_id = update.message.voice.file_id
    
    await update.message.reply_text("Entendi! Processando seu áudio... 🎙️")

    oga_path = f"{file_id}.oga"
    wav_path = f"{file_id}.wav"
    
    try:
        voice_file = await context.bot.get_file(file_id)
        await voice_file.download_to_drive(oga_path)
        
        audio = AudioSegment.from_ogg(oga_path)
        audio.export(wav_path, format="wav")
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            texto_transcrito = recognizer.recognize_google(audio_data, language='pt-BR')
            await update.message.reply_text(f"Texto entendido: \"_{texto_transcrito}_\"", parse_mode='Markdown')

    except sr.UnknownValueError:
        await update.message.reply_text("Desculpe, não consegui entender o áudio. Tente falar mais claramente.")
        return
    except sr.RequestError as e:
        await update.message.reply_text(f"Erro no serviço de reconhecimento de voz. Tente mais tarde. Erro: {e}")
        return
    except Exception as e:
        logger.error(f"Erro ao processar áudio: {e}")
        await update.message.reply_text("Ocorreu um erro inesperado ao processar seu áudio.")
        return
    finally:
        if os.path.exists(oga_path): os.remove(oga_path)
        if os.path.exists(wav_path): os.remove(wav_path)

    await update.message.reply_text("Ok, texto extraído. Consultando IA local para interpretar... 🤖")
    dados = interpretar_texto_com_ollama(texto_transcrito)

    if not dados or dados.get("error") == "connection_failed":
        await update.message.reply_text("🔴 Desculpe, não consegui me conectar à IA local. Verifique se o Ollama está rodando e tente novamente.")
        return

    if not all([dados.get("type"), dados.get("amount"), dados.get("description"), dados.get("category_name")]):
        mensagem_erro = "A IA conseguiu extrair algumas informações, mas faltam dados:\n"
        if not dados.get("type"): mensagem_erro += "- ❓ Tipo (entrada ou despesa)\n"
        if not dados.get("amount"): mensagem_erro += "- ❓ Valor\n"
        if not dados.get("description"): mensagem_erro += "- ❓ Descrição\n"
        if not dados.get("category_name"): mensagem_erro += "- ❓ Categoria\n"
        mensagem_erro += "\nPor favor, use os comandos `/entradas` ou `/despesas` para registrar manualmente."
        await update.message.reply_text(mensagem_erro)
        return

    categories_map = {cat['name'].lower(): cat['category_id'] for cat in get_categories_from_db()}
    category_id = categories_map.get(str(dados['category_name']).lower())

    if not category_id:
        await update.message.reply_text(f"A categoria '{dados['category_name']}' não foi encontrada. Verifique o nome ou use os comandos de texto.")
        return
        
    if save_transaction(user_id, dados['type'], dados['amount'], str(dados['description']).capitalize(), category_id):
        icon = "✨" if dados['type'] == 'entrada' else '💸'
        message_text = (
            f"{icon} *Lançamento por Voz (IA) Registrado!*\n\n"
            f"💰 *Valor:* `R$ {dados['amount']:.2f}`\n"
            f"📝 *Descrição:* {str(dados['description']).capitalize()}\n"
            f"🏷️ *Categoria:* {str(dados['category_name']).capitalize()}"
        )
        await update.message.reply_text(message_text, parse_mode='Markdown')
    else:
        await update.message.reply_text("🔴 *Ocorreu um erro!*\n\nNão foi possível salvar sua transação.")

# --- HANDLERS DOS COMANDOS DO TELEGRAM ---

async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    save_user(user)
    welcome_message = (
        f"E aí, *{user.first_name}*! Que bom te ver por aqui. 🐷💰\n\n"
        "Eu sou seu novo assistente financeiro, pronto para te ajudar a tomar o controle do seu dinheiro de um jeito fácil e sem complicações!\n\n"
        "Chega de planilhas! Vamos juntos organizar tudo por aqui.\n\n"
        "✍️ *O QUE VOCÊ PODE FAZER:*\n\n"
        " • `/entradas` - Registre todo dinheiro que entra.\n"
        " • `/despesas` - Aponte qualquer gasto que você tiver.\n"
        " • `MENSAGEM DE VOZ` - Diga o que gastou para um registro rápido com IA!\n"
        " • `/pagamento` - Renove ou adquira sua assinatura.\n\n"
        "🆘 *PRECISA DE AJUDA?*\n\n"
        " • `/suporte` - Fale com nossa equipe.\n\n"
        "📊 *ACOMPANHE SEUS RESULTADOS:*\n\n"
        " • `/saldo` - Veja o panorama geral.\n"
        " • `/dia` - Consulte o resumo financeiro de hoje.\n"
        " • `/semana` - Veja o relatório dos últimos 7 dias.\n"
        " • `/mes` - Analise o balanço completo do mês atual."
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def suporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    support_message = (
        "🆘 *Suporte ao Cliente*\n\n"
        "Precisa de ajuda? Entre em contato conosco através dos canais abaixo:\n\n"
        f"👤 *Nome:* {SUPPORT_NAME}\n"
        f"📧 *E-mail:* {SUPPORT_EMAIL}\n"
        f"📱 *Telefone:* {SUPPORT_PHONE}"
    )
    await update.message.reply_text(support_message, parse_mode='Markdown')

# --- LÓGICA PARA REGISTRO DE TRANSAÇÕES ---
GET_AMOUNT, GET_DESCRIPTION, GET_CATEGORY = range(3)

async def start_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_subscription(update, context):
        return ConversationHandler.END
    command = update.message.text.lower()
    trans_type = 'entrada' if 'entrada' in command else 'despesa'
    context.user_data['type'] = trans_type
    prompt_icon = "🟢" if trans_type == 'entrada' else '🔴'
    message_text = f"{prompt_icon} Certo! Para começar, me informe o *valor* desta *{trans_type}*:"
    await update.message.reply_text(message_text, parse_mode='Markdown')
    return GET_AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError("Valor deve ser positivo")
        context.user_data['amount'] = amount
        await update.message.reply_text(
            "Valor anotado! ✅\n\nAgora, me diga uma *breve descrição* para este lançamento.",
            parse_mode='Markdown'
        )
        return GET_DESCRIPTION
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Por favor, envie um número positivo (ex: 150.50 ou 150,50).")
        return GET_AMOUNT

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['description'] = update.message.text
    categories = get_categories_from_db()
    if not categories:
        await update.message.reply_text("Não foi possível encontrar as categorias. A transação será salva sem uma.")
        return await save_final_transaction(update, context, no_category=True)
    context.user_data['categories_map'] = {cat['name']: cat['category_id'] for cat in categories}
    keyboard = [[cat['name']] for cat in categories]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Entendido! 👍\n\nPara finalizar, *em qual categoria* isso se encaixa?",
        reply_markup=reply_markup
    )
    return GET_CATEGORY

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chosen_category_name = update.message.text
    categories_map = context.user_data.get('categories_map', {})
    if chosen_category_name in categories_map:
        context.user_data['category_id'] = categories_map[chosen_category_name]
        context.user_data['category_name'] = chosen_category_name
        return await save_final_transaction(update, context)
    else:
        await update.message.reply_text("Categoria inválida. Por favor, selecione uma das opções do teclado.")
        return GET_CATEGORY

async def save_final_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, no_category: bool = False) -> int:
    user_id = update.effective_user.id
    data = context.user_data
    category_id = data.get('category_id') if not no_category else None

    if save_transaction(user_id, data['type'], data['amount'], data['description'], category_id):
        if data['type'] == 'entrada':
            message_text = (
                f"✨ *Nova Entrada Registrada!*\n\n"
                f"Tudo certo, seus ganhos foram atualizados.\n\n"
                f"💰 *Valor:* `R$ {data['amount']:.2f}`\n"
                f"📝 *Descrição:* {data['description']}\n"
            )
        else: # Despesa
            message_text = (
                f"💸 *Nova Despesa Registrada!*\n\n"
                f"Ok, lançamento salvo no seu controle de gastos.\n\n"
                f"💰 *Valor:* `R$ {data['amount']:.2f}`\n"
                f"📝 *Descrição:* {data['description']}\n"
            )
        if data.get('category_name'):
             message_text += f"🏷️ *Categoria:* {data['category_name']}"
    else:
        message_text = "🔴 *Ocorreu um erro!*\n\nNão foi possível salvar sua transação. Por favor, tente novamente mais tarde."
        
    await update.message.reply_text(message_text, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("--- FUNÇÃO CANCELAR ACIONADA ---")
    payment_id = context.user_data.get('pending_payment_id')
    job_name = context.user_data.get('pending_payment_job_name')

    if job_name:
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()
            logger.info(f"Job de verificação '{job_name}' removido pelo usuário.")

    if payment_id:
        try:
            sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)
            cancel_data = {"status": "cancelled"}
            payment_response = sdk.payment().update(payment_id, cancel_data)

            if payment_response["status"] == 200 and payment_response["response"].get("status") == 'cancelled':
                update_mensalidade_status(payment_id, 'cancelado')
                await update.message.reply_text(
                    "✅ *Cobrança Cancelada!*\n\nO PIX pendente foi cancelado com sucesso. Você pode iniciar um novo pagamento quando desejar usando o comando `/pagamento`.", 
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode='Markdown'
                )
            else:
                status = payment_response["response"].get("status", "desconhecido")
                logger.error(f"Não foi possível cancelar o PIX no MP: {payment_response['response']}")
                await update.message.reply_text(f"Operação encerrada. A cobrança PIX não pôde ser cancelada (status: {status}).", reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            logger.error(f"Exceção ao cancelar PIX no MP: {e}")
            await update.message.reply_text("Operação encerrada. Houve um problema ao tentar cancelar a cobrança PIX.", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text(
            "Operação cancelada.",
            reply_markup=ReplyKeyboardRemove()
        )

    context.user_data.clear()
    return ConversationHandler.END

# --- LÓGICA DE PAGAMENTO COM CUPONS ---
ASK_COUPON, GET_COUPON_CODE, WAITING_FOR_PAYMENT = range(3, 6)

async def check_payment_status_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    payment_id = job_data['payment_id']
    chat_id = job_data['chat_id']
    user_id = job_data['user_id']
    start_time = job_data['start_time']
    amount = job_data['amount']

    if datetime.now() > start_time + timedelta(minutes=10):
        await context.bot.send_message(chat_id, "⏰ O tempo para este PIX expirou e a cobrança foi cancelada. Por favor, gere um novo usando /pagamento.")
        update_mensalidade_status(payment_id, 'expirado')
        try:
            sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)
            cancel_data = {"status": "cancelled"}
            sdk.payment().update(payment_id, cancel_data)
        except Exception as e:
            logger.error(f"Erro ao cancelar pagamento no MP: {e}")
        context.job.schedule_removal()
        return

    try:
        sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)
        payment_response = sdk.payment().get(payment_id)
        payment = payment_response["response"]
        if payment_response["status"] == 200:
            status = payment['status']
            if status == 'approved':
                await context.bot.send_message(chat_id, "✅ Pagamento encontrado e validado! Sua mensalidade foi confirmada.")
                update_mensalidade_status(payment_id, 'pago')
                category_id = get_category_id_by_name("Mensalidade")
                save_transaction(user_id=user_id, trans_type='despesa', amount=amount, description=f'Pagamento Mensalidade (ID: {payment_id})', category_id=category_id)
                if OWNER_USER_ID != 0:
                    save_transaction(user_id=OWNER_USER_ID, trans_type='entrada', amount=amount, description=f'Recebimento Mensalidade de {user_id}', category_id=category_id)
                context.job.schedule_removal()
            elif status in ['cancelled', 'rejected', 'refunded']:
                await context.bot.send_message(chat_id, f"❌ O pagamento foi *{status}*. Por favor, gere um novo usando /pagamento.")
                update_mensalidade_status(payment_id, 'cancelado')
                context.job.schedule_removal()
    except Exception as e:
        logger.error(f"Erro ao verificar pagamento no job: {e}")

def generate_pix_payload(amount):
    try:
        sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)
        request_options = mercadopago.config.RequestOptions()
        request_options.custom_headers = {'x-idempotency-key': str(uuid.uuid4())}
        payment_data = {
            "transaction_amount": float(amount),
            "description": "Pagamento Mensalidade App",
            "payment_method_id": "pix",
            "payer": {"email": PAYER_EMAIL}
        }
        payment_response = sdk.payment().create(payment_data, request_options)
        payment = payment_response["response"]
        if payment_response["status"] == 201:
            payment_id = payment["id"]
            qr_code_base64 = payment["point_of_interaction"]["transaction_data"]["qr_code_base64"]
            qr_code_text = payment["point_of_interaction"]["transaction_data"]["qr_code"]
            image_data = base64.b64decode(qr_code_base64)
            image_stream = io.BytesIO(image_data)
            return qr_code_text, image_stream, payment_id
        else:
            logger.error(f"Erro ao gerar PIX no Mercado Pago: {payment}")
            return None, None, None
    except Exception as e:
        logger.error(f"Erro ao gerar PIX: {e}")
        return None, None, None

async def start_payment_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    expiration_date = get_active_subscription_end_date(user_id)
    if expiration_date:
        today = datetime.now()
        remaining_days = (expiration_date - today).days
        await update.message.reply_text(
            f"✅ *Sua assinatura já está ativa!*\n\nSeu acesso está garantido por mais *{remaining_days} dia(s)*.\nExpira em: {expiration_date.strftime('%d/%m/%Y')}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    keyboard = [["Sim", "Não"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Para continuar, vamos confirmar o pagamento da sua assinatura.\n\n"
        "Você possui um cupom de desconto?",
        reply_markup=reply_markup
    )
    return ASK_COUPON

async def handle_coupon_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == "Sim":
        await update.message.reply_text(
            "Ótimo! Por favor, digite seu cupom de desconto:",
            reply_markup=ReplyKeyboardRemove()
        )
        return GET_COUPON_CODE
    else:
        await update.message.reply_text("Entendido. Gerando sua cobrança no valor padrão...", reply_markup=ReplyKeyboardRemove())
        return await generate_and_send_pix(update, context, BASE_PRICE)

async def process_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    coupon_code = update.message.text.upper()
    coupons = context.bot_data.get('coupons', {})
    coupon = coupons.get(coupon_code)

    if not coupon:
        await update.message.reply_text(
            "❌ Cupom inválido. Por favor, inicie o processo novamente com /pagamento.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    if coupon["type"] == "value":
        final_price = BASE_PRICE - coupon["discount_value"]
        await update.message.reply_text(
            f"✅ Cupom *{coupon_code}* aplicado com sucesso! Gerando sua cobrança com desconto...",
            reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown'
        )
        return await generate_and_send_pix(update, context, final_price)
    
    elif coupon["type"] == "free_days":
        free_days = coupon["free_days"]
        grant_free_days(update.effective_user.id, free_days, coupon_code)
        await update.message.reply_text(
            f"🎉 Cupom *{coupon_code}* aplicado! Você ganhou *{free_days} dias* de acesso gratuito. Aproveite!",
            reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown'
        )
        return ConversationHandler.END

async def generate_and_send_pix(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: float) -> int:
    user_id = update.effective_user.id
    await context.bot.send_message(chat_id=user_id, text=f"Gerando seu PIX de R$ {amount:.2f}... Aguarde um momento. ⏳")

    brcode_data, qr_code_image, payment_id = generate_pix_payload(amount)

    if brcode_data and qr_code_image:
        job_name = f"check_{payment_id}"
        context.user_data['pending_payment_id'] = payment_id
        context.user_data['pending_payment_job_name'] = job_name
        
        save_pending_mensalidade(user_id, payment_id, amount)
        await context.bot.send_photo(
            chat_id=user_id,
            photo=qr_code_image,
            caption=(
                f"✅ *PIX para sua mensalidade gerado!*\n\n"
                f"Você está pagando sua assinatura do app.\n\n"
                f" destinatário: *{RECIPIENT_DISPLAY_NAME}*\n"
                f"💰 *Valor:* `R$ {amount:.2f}`\n\n"
                f"🔒 Pagamento seguro processado via *Mercado Pago*."
            ),
            parse_mode='Markdown'
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "👇 *PIX Copia e Cola* 👇\n\n"
                f"`{brcode_data}`\n\n"
                "Basta copiar o código acima e colar na área PIX do seu banco.\n\n"
                "Assim que o pagamento for confirmado, você receberá uma mensagem.\n\n"
                "ℹ️ Se desejar cancelar esta cobrança, digite /cancelar."
            ),
            parse_mode='Markdown'
        )
        job_data = {
            'chat_id': user_id, 'user_id': user_id, 'payment_id': payment_id,
            'start_time': datetime.now(), 'amount': amount
        }
        context.job_queue.run_repeating(check_payment_status_job, interval=30, first=10, data=job_data, name=job_name)
        return WAITING_FOR_PAYMENT
    else:
        await context.bot.send_message(chat_id=user_id, text="🔴 Desculpe, ocorreu um erro ao gerar o PIX. Verifique os dados e tente novamente.")
        return ConversationHandler.END

async def waiting_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Estou aguardando a confirmação do seu pagamento. Se desejar, você pode cancelar a cobrança com o comando /cancelar."
    )
    return WAITING_FOR_PAYMENT

# --- COMANDOS DE RELATÓRIO E SALDO ---
async def get_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_subscription(update, context):
        return
    user_id = update.effective_user.id
    conn = get_db_connection()
    if not conn:
        await update.message.reply_text("Não foi possível conectar ao banco de dados.")
        return
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT type, SUM(amount) as total FROM transactions WHERE user_id = %s GROUP BY type;"
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        total_entradas = sum(float(r['total']) for r in results if r['type'] == 'entrada')
        total_despesas = sum(float(r['total']) for r in results if r['type'] == 'despesa')
        saldo = total_entradas - total_despesas
        saldo_message = (
            f"🏦 *Seu Saldo Total*\n\n"
            f"🟢 *Total de Entradas:* `R$ {total_entradas:.2f}`\n"
            f"🔴 *Total de Despesas:* `R$ {total_despesas:.2f}`\n"
            f"------------------------------------\n"
            f"💰 *Saldo Atual:* `R$ {saldo:.2f}`\n"
            f"------------------------------------"
        )
        await update.message.reply_text(saldo_message, parse_mode='Markdown')
    except Error as e:
        logger.error(f"Erro ao calcular saldo: {e}")
        await update.message.reply_text("Ocorreu um erro ao buscar seu saldo.")
    finally:
        cursor.close()
        conn.close()

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_subscription(update, context):
        return
    command = update.message.text.lower()
    user_id = update.effective_user.id
    if '/dia' in command:
        period_label = "do Dia"
        query_date_filter = "AND DATE(t.transaction_date) = CURDATE()"
    elif '/semana' in command:
        period_label = "da Semana (últimos 7 dias)"
        query_date_filter = "AND t.transaction_date >= CURDATE() - INTERVAL 7 DAY"
    elif '/mes' in command:
        period_label = "do Mês Atual"
        query_date_filter = "AND YEAR(t.transaction_date) = YEAR(CURDATE()) AND MONTH(t.transaction_date) = MONTH(CURDATE())"
    else:
        return
    conn = get_db_connection()
    if not conn:
        await update.message.reply_text("Não foi possível conectar ao banco de dados.")
        return
    cursor = conn.cursor(dictionary=True)
    try:
        query_summary = f"SELECT type, SUM(amount) as total FROM transactions t WHERE user_id = %s {query_date_filter} GROUP BY type;"
        cursor.execute(query_summary, (user_id,))
        summary = cursor.fetchall()
        total_entradas = sum(float(r['total']) for r in summary if r['type'] == 'entrada')
        total_despesas = sum(float(r['total']) for r in summary if r['type'] == 'despesa')
        saldo = total_entradas - total_despesas
        report_message = (
            f"📊 *Relatório Financeiro {period_label}*\n\n"
            f"🟢 *Total de Entradas:* `R$ {total_entradas:.2f}`\n"
            f"🔴 *Total de Despesas:* `R$ {total_despesas:.2f}`\n"
            f"------------------------------------\n"
            f"💰 *Saldo do Período:* `R$ {saldo:.2f}`\n"
            f"------------------------------------\n\n"
        )
        query_categories = f"SELECT c.name, SUM(t.amount) as total FROM transactions t JOIN categories c ON t.category_id = c.category_id WHERE t.user_id = %s AND t.type = 'despesa' {query_date_filter} GROUP BY c.name ORDER BY total DESC;"
        cursor.execute(query_categories, (user_id,))
        category_summary = cursor.fetchall()
        if category_summary:
            report_message += "*Resumo de Despesas por Categoria:*\n"
            for row in category_summary:
                percent = (float(row['total']) / total_despesas * 100) if total_despesas > 0 else 0
                report_message += f"`-` {row['name']}: `R$ {float(row['total']):.2f}` `({percent:.1f}%)`\n"
        await update.message.reply_text(report_message, parse_mode='Markdown')
    except Error as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        await update.message.reply_text("Ocorreu um erro ao buscar os dados para o relatório.")
    finally:
        cursor.close()
        conn.close()

# --- FUNÇÃO PRINCIPAL (MAIN) ---

def main() -> None:
    request = HTTPXRequest(connect_timeout=10.0, read_timeout=20.0)
    application = Application.builder().token(TELEGRAM_TOKEN).request(request).build()
    
    application.bot_data['coupons'] = COUPONS

    conv_handler_transaction = ConversationHandler(
        entry_points=[CommandHandler(["entradas", "entrada"], start_transaction), CommandHandler(["despesas", "despesa"], start_transaction)],
        states={
            GET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            GET_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            GET_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    payment_handler = ConversationHandler(
        entry_points=[CommandHandler("pagamento", start_payment_flow)],
        states={
            ASK_COUPON: [MessageHandler(filters.Regex('^(Sim|Não)$'), handle_coupon_choice)],
            GET_COUPON_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_coupon_code)],
            WAITING_FOR_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, waiting_message)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    
    # --- Adição dos Handlers ---
    application.add_handler(CommandHandler("inicio", inicio))
    application.add_handler(CommandHandler("suporte", suporte))
    application.add_handler(CommandHandler("saldo", get_saldo))
    application.add_handler(conv_handler_transaction)
    application.add_handler(payment_handler)
    application.add_handler(CommandHandler("dia", generate_report))
    application.add_handler(CommandHandler("semana", generate_report))
    application.add_handler(CommandHandler("mes", generate_report))

    # Handler para mensagens de voz
    application.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, handle_voice))
    
    application.run_polling()

if __name__ == "__main__":
        main()