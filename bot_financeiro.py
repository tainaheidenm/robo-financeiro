from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import pandas as pd
from datetime import datetime
import os
import re
import threading
from flask import Flask

# pega token do Render
TOKEN = os.getenv("TOKEN")

arquivo = "base_dados.xlsx"
arquivo_regras = "regras.xlsx"

# cria base se não existir
if not os.path.exists(arquivo):
    df = pd.DataFrame(columns=["Data", "Descricao", "Valor", "Categoria"])
    df.to_excel(arquivo, index=False)

# cria regras se não existir
if not os.path.exists(arquivo_regras):
    regras = pd.DataFrame({
        "Palavra": ["ifood", "mercado", "uber", "cera"],
        "Categoria": ["Alimentação", "Alimentação", "Transporte", "Empresa"]
    })
    regras.to_excel(arquivo_regras, index=False)

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.lower()

    try:
        # pega valor em qualquer lugar da frase
        match = re.search(r"(\d+[.,]?\d*)", texto)

        if not match:
            await update.message.reply_text("❌ Não encontrei valor. Ex: 50 mercado")
            return

        valor_texto = match.group(1).replace(",", ".")
        valor = float(valor_texto)

        # remove o valor da frase
        descricao = texto.replace(match.group(1), "").strip()

        # identificar entrada ou saída
        if any(palavra in texto for palavra in ["recebi", "ganhei", "entrada", "pix recebido"]):
            tipo = "Entrada"
            valor_final = valor
        else:
            tipo = "Saída"
            valor_final = -valor

        # ler regras
        regras = pd.read_excel(arquivo_regras)

        categoria = "Outros"
        for _, row in regras.iterrows():
            palavra = str(row["Palavra"]).strip().lower()
            if palavra in descricao:
                categoria = row["Categoria"]
                break

        # salvar
        novo = pd.DataFrame([{
            "Data": datetime.now().strftime("%d/%m/%Y"),
            "Descricao": descricao,
            "Valor": valor_final,
            "Categoria": categoria
        }])

        df = pd.read_excel(arquivo)
        df = pd.concat([df, novo], ignore_index=True)
        df.to_excel(arquivo, index=False)

        await update.message.reply_text(f"✅ {tipo}: {descricao} | R${valor}")

    except Exception as e:
        print("Erro:", e)
        await update.message.reply_text("❌ Erro ao processar mensagem")

# ===== TELEGRAM =====
def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    print("🤖 Bot rodando...")
    app.run_polling()

# ===== FLASK (pra manter vivo no Render) =====
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot rodando!"

def run_web():
    app_web.run(host="0.0.0.0", port=10000)

# roda tudo junto
threading.Thread(target=run_bot).start()
run_web()
