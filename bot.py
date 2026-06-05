import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests
import os

# --- KONFIGURASI ---
BOT_TOKEN = '8867256199:AAHAp_rvQxiyZkT7xlYYkSo85-OrzQydv5Y'
API_KEY_OTP = '922a0af8d090b32ee2e6114a6e572799'
ADMIN_ID = 6983958 # GANTI DENGAN ID TELEGRAM BOS
bot = telebot.TeleBot(BOT_TOKEN)

# --- DATABASE ---
conn = sqlite3.connect('nokos.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, saldo INTEGER)')
conn.commit()

# --- FUNGSI ---
def get_saldo(user_id):
    c.execute('SELECT saldo FROM users WHERE id=?', (user_id,))
    res = c.fetchone()
    return res[0] if res else 0

def update_saldo(user_id, jumlah):
    c.execute('INSERT OR IGNORE INTO users (id, saldo) VALUES (?, 0)', (user_id,))
    c.execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (jumlah, user_id))
    conn.commit()

# --- HANDLER ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    saldo = get_saldo(user_id)
    
    text = (f"✨ *Nokos Pro Premium*\n\n"
            f"👤 ID: `{user_id}`\n"
            f"💰 Saldo Anda: *Rp {saldo:,}*\n\n"
            f"Pilih layanan di bawah:")
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📱 Order WhatsApp (Rp 4.200)", callback_data="order_wa"))
    markup.add(InlineKeyboardButton("💳 Panduan Deposit", callback_data="info_va"), 
               InlineKeyboardButton("🆘 Bantuan", callback_data="bantuan"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['addsaldo'])
def cmd_add_saldo(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) == 3:
        update_saldo(int(args[1]), int(args[2]))
        bot.reply_to(message, f"Berhasil menambah saldo {args[2]} untuk ID {args[1]}")

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    if call.data == "order_wa":
        harga = 4200 # 3000 (modal) + 1200 (profit)
        if get_saldo(user_id) < harga:
            bot.answer_callback_query(call.id, "Saldo tidak cukup!")
            return
        
        # Panggil API JasaOTP
        res = requests.get(f"https://api.jasaotp.id/v1/order.php?api_key={API_KEY_OTP}&negara=6&layanan=wa&operator=any").json()
        if res.get('success'):
            update_saldo(user_id, -harga)
            nomor = res['data']['number']
            order_id = res['data']['order_id']
            bot.send_message(call.message.chat.id, f"✅ Order Sukses!\nNomor: `{nomor}`\nID: `{order_id}`")
        else:
            bot.send_message(call.message.chat.id, "Stok habis / API Error.")

    elif call.data == "info_va":
        text = ("🏦 *PANDUAN DEPOSIT*\n\n"
                "Transfer ke Bank Permata:\n`8985082065151676`\n\n"
                "Konfirmasi ke Admin: @putraisalwayshappy")
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

    elif call.data == "bantuan":
        bot.send_message(call.message.chat.id, "Butuh bantuan? Hubungi: @putraisalwayshappy")

bot.infinity_polling()
