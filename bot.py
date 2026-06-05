import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests

# KONFIGURASI ELITE
BOT_TOKEN = '8867256199:AAHAp_rvQxiyZkT7xlYYkSo85-OrzQydv5Y'
API_KEY_OTP = '922a0af8d090b32ee2e6114a6e572799'
ADMIN_ID = 6903958589 
ADMIN_USERNAME = "@putraisalwayshappy"
bot = telebot.TeleBot(BOT_TOKEN)

# DB SETUP
conn = sqlite3.connect('nokos.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, saldo INTEGER)')
conn.commit()

# FUNGSI DEPOSIT & SALDO
def get_saldo(uid):
    c.execute('SELECT saldo FROM users WHERE id=?', (uid,))
    res = c.fetchone()
    return res[0] if res else 0

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    saldo = get_saldo(uid)
    text = (f"✨ *Halo Kak! Selamat datang di Nokos Pro Elite!*\n\n"
            f"Layanan OTP tercepat untuk WhatsApp & lainnya.\n"
            f"💰 *Saldo Anda:* Rp {saldo:,}\n\n"
            f"Pilih fitur favorit di bawah ya: 👇")
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Order Nomor WA", callback_data="order_v1"))
    markup.add(InlineKeyboardButton("💳 Isi Saldo (Deposit)", callback_data="menu_deposit"))
    markup.add(InlineKeyboardButton("🆘 Bantuan & Tutorial", callback_data="bantuan"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

# --- FITUR ADMIN (KODE 2705) ---
@bot.message_handler(commands=['addsaldo'])
def add_saldo(message):
    # Keamanan: Harus ID Bos dan pakai kode 2705 di pesan
    if message.from_user.id == ADMIN_ID and "2705" in message.text:
        args = message.text.split()
        uid_target, jumlah = int(args[1]), int(args[2])
        c.execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (jumlah, uid_target))
        conn.commit()
        bot.reply_to(message, f"✅ *Sukses!* Saldo ID {uid_target} ditambah Rp {jumlah:,}")

# --- CALLBACK MENU ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "bantuan":
        text = (f"🆘 *TUTORIAL NOKOS PRO*\n\n"
                f"1. *Deposit:* Klik 'Isi Saldo', pilih nominal, transfer ke Permata, kirim bukti ke {ADMIN_USERNAME}.\n"
                f"2. *Order:* Klik 'Order Nomor', saldo akan terpotong, lalu masukkan nomor ke WA.\n"
                f"3. *OTP:* Klik tombol 'Cek OTP' setelah SMS terkirim.\n"
                f"4. *Refund:* Jika OTP tidak masuk, klik 'Cancel Order'. Saldo otomatis balik!\n\n"
                f"Ada kendala? Langsung curhat aja ke admin: {ADMIN_USERNAME} ya kak! 😊")
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# [Fungsi Order, Cek OTP, Cancel sudah termasuk di versi sebelumnya]
bot.remove_webhook()
bot.infinity_polling()
