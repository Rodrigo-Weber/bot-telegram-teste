import mercadopago

# --- SUAS CREDENCIAIS ---
MERCADO_PAGO_ACCESS_TOKEN = "APP_USR-759602526921954-082507-0fc45feda769868688acb72646b7a6d8-302693772"

# --- LISTA DE IDs PARA CANCELAR ---
# Cole aqui os IDs que você pegou do banco de dados
payment_ids_para_cancelar = [
    "123058169439",
    "123616000294",
    "123062872787",
    "123059041205",
    "123079049137",
]

# --- SCRIPT DE CANCELAMENTO ---
sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)

for payment_id in payment_ids_para_cancelar:
    try:
        print(f"Tentando cancelar o pagamento ID: {payment_id}...")
        cancel_data = {"status": "cancelled"}
        payment_response = sdk.payment().update(payment_id, cancel_data)
        
        if payment_response["status"] == 200 and payment_response["response"].get("status") == 'cancelled':
            print(f"✅ SUCESSO: Pagamento {payment_id} foi cancelado.")
            # Aqui você também pode rodar um UPDATE no seu banco para mudar o status para 'cancelado'
        else:
            print(f"❌ FALHA: Não foi possível cancelar o pagamento {payment_id}. Resposta: {payment_response['response']}")
            
    except Exception as e:
        print(f"🚨 ERRO: Ocorreu uma exceção ao tentar cancelar o pagamento {payment_id}: {e}")

print("\nProcesso finalizado.")