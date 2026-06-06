import telebot, sqlite3, requests, time, threading, os
from datetime import datetime

# --- 1. CONFIGURATION & ENV ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
API_KEY_OTP = os.environ.get('API_KEY_OTP')
BANK_ACCOUNT = os.environ.get('BANK_ACCOUNT', '8985082065151676 (Permata)')
ADMIN_ID = 6903958589 
ADMIN_USERNAME = "@putraisalwayshappy"

if not BOT_TOKEN or not API_KEY_OTP:
    raise Exception("❌ BOT_TOKEN atau API_KEY_OTP belum diset!")

bot = telebot.TeleBot(BOT_TOKEN)

# --- 2. DB SAFETY, WAL MODE & MIGRATION ---
db_lock = threading.Lock()
conn = sqlite3.connect('nokos.db', check_same_thread=False)

with db_lock:
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, saldo INTEGER, join_date TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY, uid INTEGER, chat_id INTEGER, number TEXT, 
                    service TEXT, harga INTEGER, status TEXT, otp TEXT, created_at TEXT)''')
    conn.commit()

# --- 3. UTILITY ---
last_action = {}
def rate_limit_ok(uid):
    now = time.time()
    if uid in last_action and now - last_action[uid] < 1.5: return False
    last_action[uid] = now
    return True

def panggil_api(endpoint, params=None):
    url = f"https://api.jasaotp.id/v1/{endpoint}"
    params = params or {}
    params['api_key'] = API_KEY_OTP
    for _ in range(3):
        try:
            res = requests.get(url, params=params, timeout=10).json()
            return res if endpoint == "layanan.php" else (res if res.get('success') else {"success": False})
        except: time.sleep(1)
    return {"success": False}

def escape_markdown(text):
    text = str(text)
    karakter = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in karakter: text = text.replace(char, f"\\{char}")
    return text

def safe_edit_message(text, chat_id, message_id, markup=None):
    try: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='MarkdownV2')
    except Exception as e: print(f"[TG ERROR] Edit Message: {e}")

# --- 4. MONITORING OTP ---
def monitor_otp(chat_id, order_id, uid, harga):
    for i in range(20): # 10 Menit
        time.sleep(30)
        res = panggil_api("sms.php", {'id': order_id})
        if res.get('success') and res.get('data') and res['data'].get('otp'):
            otp = str(res['data']['otp'])
            with db_lock:
                c = conn.cursor()
                c.execute('UPDATE orders SET status="completed", otp=? WHERE order_id=? AND status="pending"', (otp, order_id))
                if c.rowcount > 0:
                    c.execute('SELECT number FROM orders WHERE order_id=?', (order_id,))
                    no = c.fetchone()[0]
                    conn.commit()
                    bot.send_message(chat_id, f"🎉 *OTP Berhasil!*\n📱 `{escape_markdown(no)}`\n✉️ `{escape_markdown(otp)}`", parse_mode='MarkdownV2')
            return 
    
    with db_lock:
        c = conn.cursor()
        c.execute('UPDATE orders SET status="cancelled" WHERE order_id=? AND status="pending"', (order_id,))
        if c.rowcount > 0:
            panggil_api("cancel.php", {'id': order_id})
            c.execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (harga, uid))
            conn.commit()
            bot.send_message(chat_id, f"❌ Order `{escape_markdown(order_id)}` kadaluarsa, saldo dikembalikan.", parse_mode='MarkdownV2')

def resume_pending_orders():
    with db_lock:
        c = conn.cursor()
        c.execute('SELECT order_id, uid, chat_id, harga FROM orders WHERE status="pending"')
        for oid, uid, chat_id, harga in c.fetchall():
            threading.Thread(target=monitor_otp, args=(chat_id or uid, oid, uid, harga), daemon=True).start()

# --- 5. COMMANDS ---
@bot.message_handler(commands=['start', 'saldo'])
def start(message):
    uid = message.from_user.id
    if not rate_limit_ok(uid): return
    with db_lock:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO users (id, saldo, join_date) VALUES (?, 0, ?)', (uid, datetime.now().strftime("%Y-%m-%d")))
        c.execute('SELECT saldo FROM users WHERE id=?', (uid,))
        saldo = c.fetchone()[0]
        conn.commit()
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("🛒 Beli Nomor", callback_data="negara"),
        telebot.types.InlineKeyboardButton("👤 Profil", callback_data="profil"),
        telebot.types.InlineKeyboardButton("💳 Deposit", callback_data="menu_deposit"),
        telebot.types.InlineKeyboardButton("📖 Panduan", callback_data="panduan"),
        telebot.types.InlineKeyboardButton("🆘 Bantuan", callback_data="bantuan")
    )
    bot.send_message(message.chat.id, f"💰 Saldo Anda: Rp {saldo:,}", reply_markup=markup)

@bot.message_handler(commands=['addsaldo'])
def add_saldo(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        uid, jml = int(args[1]), int(args[2])
        with db_lock:
            c = conn.cursor()
            c.execute('INSERT OR IGNORE INTO users (id, saldo, join_date) VALUES (?, 0, ?)', (uid, datetime.now().strftime("%Y-%m-%d")))
            c.execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (jml, uid))
            conn.commit()
        bot.reply_to(message, f"✅ Saldo user `{uid}` berhasil ditambah Rp {jml:,}.")
    except: bot.reply_to(message, "❌ Format salah: /addsaldo [ID] [JML]")

# --- 6. CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid, chat_id = call.from_user.id, call.message.chat.id
    if not rate_limit_ok(uid): return
    d = call.data.split("_")
    
    if call.data == "profil":
        with db_lock:
            c = conn.cursor()
            c.execute('SELECT saldo, join_date FROM users WHERE id=?', (uid,))
            user = c.fetchone()
            c.execute("SELECT COUNT(*), SUM(status='completed'), SUM(status='pending'), SUM(status='cancelled') FROM orders WHERE uid=?", (uid,))
            stats = c.fetchone()
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"👤 *PROFIL AKUN*\n\n🆔 ID: `{uid}`\n💰 Saldo: *Rp {user[0]:,}*\n📅 Join: `{user[1]}`\n\n📦 *Statistik:*\n✅ Berhasil: {stats[1] or 0}\n⏳ Pending: {stats[2] or 0}\n❌ Cancel: {stats[3] or 0}", parse_mode='MarkdownV2')

    elif call.data == "panduan":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📖 *PANDUAN PENGGUNAAN*\n1. Deposit saldo.\n2. Beli nomor.\n3. Tunggu OTP (Maks 10 menit).\n4. Jika OTP gagal, refund otomatis.", parse_mode='MarkdownV2')

    elif call.data == "bantuan":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"🆘 *BANTUAN*\nHubungi: {escape_markdown(ADMIN_USERNAME)}", parse_mode='MarkdownV2')

    elif call.data == "negara":
        res = panggil_api("negara.php")
        if not res.get("success"): return bot.answer_callback_query(call.id, "Gangguan server!", show_alert=True)
        markup = telebot.types.InlineKeyboardMarkup()
        for n in res['data']: markup.add(telebot.types.InlineKeyboardButton(n['nama_negara'], callback_data=f"op_{n['id_negara']}"))
        safe_edit_message("Pilih Negara:", chat_id, call.message.message_id, markup)

    elif call.data.startswith("order_") and len(d) >= 4:
        # Validasi respons API ketat (Poin 4)
        layanan = panggil_api("layanan.php", {'negara': d[1]})
        if d[1] not in layanan or d[2] not in layanan[d[1]]:
            return bot.answer_callback_query(call.id, "Gagal ambil harga!", show_alert=True)
        harga = int(layanan[d[1]][d[2]]['harga'])
        
        with db_lock:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM orders WHERE uid=? AND status='pending'", (uid,))
            if c.fetchone()[0] > 0: return bot.answer_callback_query(call.id, "Selesaikan order pending dulu!", show_alert=True)
            c.execute('UPDATE users SET saldo = saldo - ? WHERE id = ? AND saldo >= ?', (harga, uid, harga))
            if c.rowcount == 0: return bot.answer_callback_query(call.id, "Saldo tidak cukup!", show_alert=True)
            conn.commit()
        
        res = panggil_api("order.php", {'negara': d[1], 'layanan': d[2], 'operator': d[3]})
        if res.get('success') and 'data' in res and 'order_id' in res['data'] and 'number' in res['data']:
            oid, nomor = str(res['data']['order_id']), res['data']['number']
            with db_lock:
                c = conn.cursor()
                c.execute('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)', (oid, uid, chat_id, nomor, d[2], harga, 'pending', '', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
            bot.edit_message_text("✅ Order berhasil! Menunggu OTP...", chat_id, call.message.message_id)
            threading.Thread(target=monitor_otp, args=(chat_id, oid, uid, harga), daemon=True).start()
            try: bot.send_message(ADMIN_ID, f"🔔 Order Baru\nUser: `{uid}`\nLayanan: {d[2]}\nHarga: Rp {harga:,}", parse_mode='MarkdownV2')
            except: pass
        else:
            with db_lock: conn.cursor().execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (harga, uid)); conn.commit()
            bot.answer_callback_query(call.id, "Stok habis atau API sibuk!", show_alert=True)

# START
resume_pending_orders()
bot.infinity_polling()
