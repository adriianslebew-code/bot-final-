import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests

# Konfigurasi Utama
BOT_TOKEN = '8867256199:AAHAp_rvQxiyZkT7xlYYkSo85-OrzQydv5Y'
API_KEY_OTP = '922a0af8d090b32ee2e6114a6e572799'
ADMIN_ID = 6903958589 
bot = telebot.TeleBot(BOT_TOKEN)

# Inisialisasi Database
conn = sqlite3.connect('nokos.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, saldo INTEGER)')
conn.commit()

# --- FUNGSI PENDUKUNG ---
def get_saldo(uid):
    c.execute('SELECT saldo FROM users WHERE id=?', (uid,))
    res = c.fetchone()
    return res[0] if res else 0

def panggil_api(endpoint, params=None):
    url = f"https://api.jasaotp.id/v2/{endpoint}"
    if not params: params = {}
    params['api_key'] = API_KEY_OTP
    try:
        return requests.get(url, params=params).json()
    except:
        return {"success": False}

# --- MENU UTAMA (FRIENDLY) ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    saldo = get_saldo(uid)
    text = (f"👋 *Halo Kak! Selamat datang di Nokos Pro.*\n\n"
            f"Kami siap membantu kebutuhan verifikasi Anda dengan cepat dan aman.\n"
            f"💰 *Saldo Anda:* Rp {saldo:,}\n\n"
            f"Yuk, pilih menu di bawah ini:")
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🛒 Beli Nomor WhatsApp", callback_data="order_wa"),
        InlineKeyboardButton("💳 Isi Saldo (Deposit)", callback_data="menu_deposit"),
        InlineKeyboardButton("🆘 Tutorial & Bantuan", callback_data="bantuan")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

# --- LOGIKA CALLBACK ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    
    if call.data == "order_wa":
        res = panggil_api("layanan.php", {'negara': 6})
        try:
            harga_api = res['6']['wa']['harga']
            total = harga_api + 1200
            if get_saldo(uid) < total:
                bot.answer_callback_query(call.id, "Maaf Kak, saldo tidak cukup!")
                return
            
            order = panggil_api("order.php", {'negara': 6, 'layanan': 'wa', 'operator': 'any'})
            if order.get('success'):
                c.execute('UPDATE users SET saldo = saldo - ? WHERE id = ?', (total, uid))
                conn.commit()
                bot.send_message(call.message.chat.id, f"✅ *Berhasil!* Nomor: `{order['data']['number']}`")
        except:
            bot.send_message(call.message.chat.id, "Sedang ada gangguan, coba lagi nanti ya Kak.")

    elif call.data == "menu_deposit":
        text = "Pilih nominal isi saldo di bawah ini ya Kak:"
        markup = InlineKeyboardMarkup(row_width=2)
        for n in [5000, 10000, 20000, 50000]:
            markup.add(InlineKeyboardButton(f"Rp {n:,}", callback_data=f"depo_{n}"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("depo_"):
        n = call.data.split("_")[1]
        bot.send_message(call.message.chat.id, f"Silakan transfer Rp {n} ke Bank Permata: `8985082065151676`. Segera chat @putraisalwayshappy untuk proses ya!")

# Tambahan untuk memastikan bot aktif
bot.remove_webhook()
bot.infinity_polling()
