import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3, requests, time, threading

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

# --- AUTO TIMEOUT & REFUND ---
def monitor_otp(chat_id, msg_id, order_id, uid, harga):
    for i in range(6): # Cek 6x tiap 30 detik (Total 3 Menit)
        time.sleep(30)
        status = panggil_api("status.php", {'order_id': order_id})
        if status.get('data', {}).get('sms'):
            return # OTP Masuk, stop monitor
    
    # Jika 3 menit tidak ada SMS, Batal & Refund
    panggil_api("cancel.php", {'order_id': order_id})
    c.execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (harga, uid))
    c.execute('DELETE FROM orders WHERE order_id=?', (order_id,))
    conn.commit()
    bot.send_message(chat_id, "❌ Waktu habis! Order otomatis dibatalkan & saldo dikembalikan.")

# --- HANDLER START & MENU DINAMIS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Beli Nomor (Pilih Negara)", callback_data="negara"))
    markup.add(InlineKeyboardButton("💳 Isi Saldo", callback_data="menu_deposit"))
    markup.add(InlineKeyboardButton("🆘 Bantuan", callback_data="bantuan"))
    bot.send_message(message.chat.id, f"✨ *Nokos Pro Elite*\n💰 Saldo Anda: Rp {get_saldo(uid):,}", reply_markup=markup, parse_mode='Markdown')

# 1. PILIH NEGARA -> 2. PILIH OPERATOR -> 3. PILIH APLIKASI
@bot.callback_query_handler(func=lambda call: call.data in ["negara", "menu_deposit", "bantuan"] or "_" in call.data)
def callback(call):
    uid = call.from_user.id
    
    # MENU NEGARA
    if call.data == "negara":
        res = panggil_api("negara.php")
        markup = InlineKeyboardMarkup()
        for n in res['data']:
            markup.add(InlineKeyboardButton(n['nama_negara'], callback_data=f"op_{n['id_negara']}"))
        bot.edit_message_text("Pilih Negara:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    # MENU OPERATOR
    elif call.data.startswith("op_"):
        id_n = call.data.split("_")[1]
        res = panggil_api("operator.php", {'negara': id_n})
        markup = InlineKeyboardMarkup()
        for op in res['data'][id_n]:
            markup.add(InlineKeyboardButton(op, callback_data=f"layanan_{id_n}_{op}"))
        bot.edit_message_text("Pilih Operator:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    # MENU APLIKASI (WA, FB, IG, DLL)
    elif call.data.startswith("layanan_"):
        d = call.data.split("_")
        id_n, op = d[1], d[2]
        res = panggil_api("layanan.php", {'negara': id_n})
        markup = InlineKeyboardMarkup()
        for key, val in res[id_n].items():
            markup.add(InlineKeyboardButton(f"{val['layanan'].upper()} (Rp {val['harga']})", callback_data=f"order_{id_n}_{key}_{op}"))
        bot.edit_message_text("Pilih Aplikasi:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    # EKSEKUSI ORDER
    elif call.data.startswith("order_"):
        d = call.data.split("_")
        res = panggil_api("order.php", {'negara': d[1], 'layanan': d[2], 'operator': d[3]})
        if res.get('success'):
            oid = res['data']['order_id']
            harga = 2000 # Sesuaikan harga
            c.execute('UPDATE users SET saldo = saldo - ? WHERE id = ?', (harga, uid))
            c.execute('INSERT INTO orders VALUES (?, ?, ?)', (oid, uid, harga))
            conn.commit()
            bot.edit_message_text(f"✅ *Order Berhasil!*\nNomor: `{res['data']['number']}`\nOrder ID: `{oid}`\n\nMenunggu SMS (Batal otomatis dlm 3 mnt).", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
            threading.Thread(target=monitor_otp, args=(call.message.chat.id, call.message.message_id, oid, uid, harga)).start()
        else:
            bot.answer_callback_query(call.id, "Stok habis!")

    # DEPOSIT & LAINNYA (Tambahkan case depo_ dan bantuan seperti sebelumnya)

bot.remove_webhook()
bot.infinity_polling()
