import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests

# Konfigurasi
BOT_TOKEN = '8867256199:AAHAp_rvQxiyZkT7xlYYkSo85-OrzQydv5Y'
API_KEY_OTP = '922a0af8d090b32ee2e6114a6e572799'
ADMIN_ID = 6903958589 
bot = telebot.TeleBot(BOT_TOKEN)

# DB & FUNGSI (Sama seperti sebelumnya)
conn = sqlite3.connect('nokos.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, saldo INTEGER)')
conn.commit()

# --- TAMPILAN UI UTAMA ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    saldo = get_saldo(uid)
    
    text = (f"✨ *SELAMAT DATANG DI NOKOS PRO V2*\n\n"
            f"Layanan OTP tercepat & terpercaya.\n"
            f"💰 Saldo Anda: *Rp {saldo:,}*\n\n"
            f"Silakan pilih menu di bawah:")
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Order Nomor (WA)", callback_data="order_wa"))
    markup.add(InlineKeyboardButton("💳 Isi Saldo (Deposit)", callback_data="menu_deposit"))
    markup.add(InlineKeyboardButton("🆘 Bantuan & Tutorial", callback_data="bantuan"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

# --- LOGIKA DEPOSIT (UI TERARAH) ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "menu_deposit":
        text = ("💳 *MENU DEPOSIT*\n\n"
                "Pilih nominal deposit Anda:\n"
                "1. Rp 5.000\n"
                "2. Rp 10.000\n"
                "3. Rp 20.000\n"
                "4. Rp 50.000\n\n"
                "Klik tombol di bawah untuk mendapatkan detail pembayaran:")
        markup = InlineKeyboardMarkup(row_width=2)
        nominal = [5000, 10000, 20000, 50000]
        for n in nominal:
            markup.add(InlineKeyboardButton(f"Rp {n:,}", callback_data=f"depo_{n}"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

    elif call.data.startswith("depo_"):
        n = call.data.split("_")[1]
        text = (f"🏦 *DETAIL PEMBAYARAN*\n\n"
                f"Transfer ke:\n"
                f"Bank: *Permata*\n"
                f"No. Rek: `8985082065151676`\n"
                f"Nominal: *Rp {n}*\n\n"
                f"⚠️ *PENTING:*\n"
                f"Setelah transfer, kirim bukti screenshot ke @putraisalwayshappy agar saldo langsung diproses.")
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

    elif call.data == "bantuan":
        text = ("🆘 *CARA ORDER & DEPOSIT*\n\n"
                "1️⃣ *Deposit:* Pilih menu 'Isi Saldo', transfer sesuai nominal, kirim bukti ke Admin.\n"
                "2️⃣ *Order:* Klik 'Order Nomor', sistem akan memotong saldo & memberi nomor.\n"
                "3️⃣ *OTP:* Tunggu SMS masuk, gunakan kodenya.\n\n"
                "Ada kendala? Hubungi: @putraisalwayshappy")
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
