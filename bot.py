import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests

# KONFIGURASI
BOT_TOKEN = '8867256199:AAHAp_rvQxiyZkT7xlYYkSo85-OrzQydv5Y'
API_KEY_OTP = '922a0af8d090b32ee2e6114a6e572799'
ADMIN_ID = 6903958589 
ADMIN_USERNAME = "@putraisalwayshappy"
bot = telebot.TeleBot(BOT_TOKEN)

# DATABASE
conn = sqlite3.connect('nokos.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, saldo INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, uid INTEGER, harga INTEGER)')
conn.commit()

# FUNGSI API
def panggil_api(endpoint, params=None):
    url = f"https://api.jasaotp.id/v2/{endpoint}"
    params = params or {}
    params['api_key'] = API_KEY_OTP
    try: return requests.get(url, params=params).json()
    except: return {"success": False}

def get_saldo(uid):
    c.execute('SELECT saldo FROM users WHERE id=?', (uid,))
    res = c.fetchone()
    return res[0] if res else 0

# --- HANDLER START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    text = (f"✨ *Halo Kak! Selamat datang di Nokos Pro Elite!*\n\n"
            f"💰 *Saldo Anda:* Rp {get_saldo(uid):,}\n\n"
            f"Pilih fitur favorit di bawah ya: 👇")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Order Nomor WA", callback_data="order_wa"))
    markup.add(InlineKeyboardButton("💳 Isi Saldo (Deposit)", callback_data="menu_deposit"))
    markup.add(InlineKeyboardButton("🆘 Bantuan & Tutorial", callback_data="bantuan"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

# --- ADMIN ---
@bot.message_handler(commands=['addsaldo'])
def admin_add(message):
    if message.from_user.id == ADMIN_ID and "2705" in message.text:
        args = message.text.split()
        uid, jml = int(args[1]), int(args[2])
        c.execute('INSERT OR IGNORE INTO users (id, saldo) VALUES (?, 0)', (uid,))
        c.execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (jml, uid))
        conn.commit()
        bot.reply_to(message, f"✅ Sukses! Saldo {uid} ditambah Rp {jml:,}")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    if call.data == "order_wa":
        res = panggil_api("order.php", {'negara': 6, 'layanan': 'wa', 'operator': 'any'})
        if res.get('success'):
            harga = 2000 # Contoh harga potong saldo
            c.execute('UPDATE users SET saldo = saldo - ? WHERE id = ?', (harga, uid))
            c.execute('INSERT INTO orders VALUES (?, ?, ?)', (res['data']['order_id'], uid, harga))
            conn.commit()
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔄 Cek OTP", callback_data=f"cek_{res['data']['order_id']}"))
            markup.add(InlineKeyboardButton("❌ Cancel & Refund", callback_data=f"refund_{res['data']['order_id']}"))
            bot.send_message(call.message.chat.id, f"✅ *Order Sukses!*\nNomor: `{res['data']['number']}`\nOrder ID: `{res['data']['order_id']}`", reply_markup=markup, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "Stok habis!")

    elif call.data.startswith("cek_"):
        oid = call.data.split("_")[1]
        res = panggil_api("status.php", {'order_id': oid})
        bot.answer_callback_query(call.id, f"Status: {res.get('data', {}).get('sms', 'Menunggu SMS')}")

    elif call.data.startswith("refund_"):
        oid = call.data.split("_")[1]
        c.execute('SELECT harga FROM orders WHERE order_id=?', (oid,))
        harga = c.fetchone()
        if harga:
            c.execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (harga[0], uid))
            c.execute('DELETE FROM orders WHERE order_id=?', (oid,))
            conn.commit()
            bot.answer_callback_query(call.id, "Refund berhasil!")
            bot.edit_message_text("❌ Order Dibatalkan & Saldo Dikembalikan.", call.message.chat.id, call.message.message_id)

    elif call.data == "menu_deposit":
        markup = InlineKeyboardMarkup(row_width=2)
        for n in [5000, 10000, 20000, 50000]:
            markup.add(InlineKeyboardButton(f"Rp {n:,}", callback_data=f"depo_{n}"))
        bot.edit_message_text(f"Pilih nominal (ID: `{uid}`):", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

    elif call.data.startswith("depo_"):
        n = call.data.split("_")[1]
        bot.send_message(call.message.chat.id, f"🏦 Transfer Rp {n} ke Permata: `8985082065151676`. Bukti ke {ADMIN_USERNAME}", parse_mode='Markdown')

    elif call.data == "bantuan":
        bot.send_message(call.message.chat.id, f"Bantuan: Hubungi {ADMIN_USERNAME} 😊")

bot.remove_webhook()
bot.infinity_polling()
