hayaperbaiki ini berarti 

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
                    order_id TEXT PRIMARY KEY, uid INTEGER, number TEXT, 
                    service TEXT, harga INTEGER, status TEXT, otp TEXT, created_at TEXT)''')
    
    try:
        c.execute("ALTER TABLE orders ADD COLUMN chat_id INTEGER")
    except sqlite3.OperationalError:
        pass 
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
    try: 
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='MarkdownV2')
    except Exception as e: 
        print(f"[TG ERROR] Edit Message: {e}")

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
                    bot.send_message(chat_id, f"🎉 *OTP Berhasil\\!*\\n📱 `{escape_markdown(no)}`\\n✉️ `{escape_markdown(otp)}`", parse_mode='MarkdownV2')
            return 
    
    # Refund Atomic
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
            target_chat = chat_id if chat_id else uid 
            threading.Thread(target=monitor_otp, args=(target_chat, oid, uid, harga), daemon=True).start()

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
        telebot.types.InlineKeyboardButton("📚 Cara Deposit", callback_data="cara_deposit")
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
    except: bot.reply_to(message, "❌ Format salah. Contoh: /addsaldo [ID] [JML]")

@bot.message_handler(commands=['cekuser'])
def cek_user(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        target_uid = int(args[1])
        with db_lock:
            c = conn.cursor()
            c.execute('SELECT saldo, join_date FROM users WHERE id=?', (target_uid,))
            user_data = c.fetchone()
        if user_data:
            bot.reply_to(message, f"👤 *DATA USER*\\n\\n🆔 ID: `{target_uid}`\\n💰 Saldo: *Rp {user_data[0]:,}*\\n📅 Join: `{user_data[1]}`", parse_mode='MarkdownV2')
        else:
            bot.reply_to(message, "❌ User tidak ditemukan di database.")
    except: bot.reply_to(message, "❌ Format salah. Contoh: /cekuser [ID]")

@bot.message_handler(commands=['cancel'])
def manual_cancel(message):
    args = message.text.split()
    if len(args) < 2: return
    oid = args[1]
    with db_lock:
        c = conn.cursor()
        c.execute('SELECT harga, uid FROM orders WHERE order_id=? AND status="pending"', (oid,))
        data = c.fetchone()
        if data:
            panggil_api("cancel.php", {'id': oid})
            c.execute('UPDATE orders SET status="cancelled" WHERE order_id=?', (oid,))
            c.execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (data[0], data[1]))
            conn.commit()
            bot.reply_to(message, "✅ Dibatalkan dan direfund.")

@bot.message_handler(commands=['riwayat'])
def riwayat(message):
    with db_lock:
        c = conn.cursor()
        c.execute('SELECT service, status, created_at FROM orders WHERE uid=? ORDER BY created_at DESC LIMIT 10', (message.from_user.id,))
        rows = c.fetchall()
        text = "\n".join([f"{r[0]} | {r[1]} | {r[2]}" for r in rows])
        bot.reply_to(message, f"📜 Riwayat:\n{text or 'Kosong'}")

@bot.message_handler(commands=['saldoapi'])
def api_bal(message):
    if message.from_user.id != ADMIN_ID: return
    res = panggil_api("balance.php")
    bot.reply_to(message, f"Saldo API: {res.get('data', {}).get('saldo', 'Error')}")

# --- 6. CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    chat_id = call.message.chat.id
    if not rate_limit_ok(uid): return
    d = call.data.split("_")
    
    # NEGARAS
    if call.data == "negara":
        res = panggil_api("negara.php")
        if not res.get("success") or "data" not in res:
            return bot.answer_callback_query(call.id, "Server sedang gangguan", show_alert=True)
        markup = telebot.types.InlineKeyboardMarkup()
        for n in res['data']: markup.add(telebot.types.InlineKeyboardButton(n['nama_negara'], callback_data=f"op_{n['id_negara']}"))
        safe_edit_message("Pilih Negara:", chat_id, call.message.message_id, markup)

    # OPERATOR
    elif call.data.startswith("op_") and len(d) >= 2:
        res = panggil_api("operator.php", {'negara': d[1]})
        if not res.get("success") or "data" not in res or d[1] not in res["data"]:
            return bot.answer_callback_query(call.id, "Operator sedang gangguan", show_alert=True)
        markup = telebot.types.InlineKeyboardMarkup()
        for op in res['data'][d[1]]: markup.add(telebot.types.InlineKeyboardButton(op, callback_data=f"layanan_{d[1]}_{op}"))
        safe_edit_message("Pilih Operator:", chat_id, call.message.message_id, markup)

    # LAYANAN
    elif call.data.startswith("layanan_") and len(d) >= 3:
        res = panggil_api("layanan.php", {'negara': d[1]})
        if d[1] not in res:
            return bot.answer_callback_query(call.id, "Layanan sedang gangguan", show_alert=True)
        markup = telebot.types.InlineKeyboardMarkup()
        for key, val in res[d[1]].items():
            # Proteksi Stok Non-Numerik (Poin 1 perbaikan)
            stok_raw = str(val.get("stok", "0"))
            try: stok_num = int(stok_raw)
            except: stok_num = 99999 # Jika 'Unlimited' atau '∞', asumsikan ready banyak
            
            if stok_num > 0:
                markup.add(telebot.types.InlineKeyboardButton(f"{val['layanan'].upper()} (Rp {int(val['harga']):,})", callback_data=f"order_{d[1]}_{key}_{d[2]}"))
        safe_edit_message("Pilih Layanan:", chat_id, call.message.message_id, markup)

    # ORDER
    elif call.data.startswith("order_") and len(d) >= 4:
        with db_lock:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM orders WHERE uid=? AND status='pending'", (uid,))
            if c.fetchone()[0] > 0:
                return bot.answer_callback_query(call.id, "Selesaikan atau batalkan order aktifmu dulu ya Kak!", show_alert=True)

        # Proteksi lambat/gagal API pembacaan harga layanan (Poin 2 perbaikan)
        layanan_data = panggil_api("layanan.php", {'negara': d[1]})
        if d[1] not in layanan_data or d[2] not in layanan_data[d[1]]:
            return bot.answer_callback_query(call.id, "Gagal mengambil harga layanan/API sibuk 🥺", show_alert=True)
            
        harga = int(layanan_data[d[1]][d[2]]['harga'])
        
        with db_lock:
            c = conn.cursor()
            c.execute('UPDATE users SET saldo = saldo - ? WHERE id = ? AND saldo >= ?', (harga, uid, harga))
            if c.rowcount == 0: return bot.answer_callback_query(call.id, "Saldo tidak cukup!", show_alert=True)
            conn.commit()
        
        res = panggil_api("order.php", {'negara': d[1], 'layanan': d[2], 'operator': d[3]})
        if res.get('success') and 'data' in res and 'order_id' in res['data']:
            oid = str(res['data']['order_id'])
            with db_lock:
                c = conn.cursor()
                c.execute('''INSERT INTO orders (order_id, uid, chat_id, number, service, harga, status, otp, created_at) 
                             VALUES (?,?,?,?,?,?,?,?,?)''', 
                          (oid, uid, chat_id, res['data']['number'], d[2], harga, 'pending', '', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
            bot.edit_message_text("✅ Order berhasil! Menunggu OTP...", chat_id, call.message.message_id)
            threading.Thread(target=monitor_otp, args=(chat_id, oid, uid, harga), daemon=True).start()
            try: bot.send_message(ADMIN_ID, f"🔔 Order Baru\\nUser: `{uid}`\\nLayanan: {d[2]}\\nHarga: Rp {harga:,}", parse_mode='MarkdownV2')
            except: pass
        else:
            with db_lock: conn.cursor().execute('UPDATE users SET saldo = saldo + ? WHERE id = ?', (harga, uid)); conn.commit()
            bot.answer_callback_query(call.id, "Stok kosong atau API pusat sibuk!", show_alert=True)
            
    # DEPOSIT & PROFIL
    elif call.data == "profil":
        with db_lock:
            c = conn.cursor()
            c.execute('SELECT saldo, join_date FROM users WHERE id=?', (uid,))
            user_data = c.fetchone()
        saldo = user_data[0] if user_data else 0
        join_date = user_data[1] if user_data else "-"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"👤 *PROFIL AKUN*\n\n🆔 *ID Akun:* `{uid}`\n💰 *Saldo:* Rp {saldo:,}\n📅 *Bergabung:* {escape_markdown(join_date)}\n\n_Catat ID Akun Kakak untuk keperluan deposit ya!_", parse_mode='MarkdownV2')

    elif call.data == "cara_deposit":
        teks = ("📚 *CARA MENGISI SALDO*\n\n"
                "1\\. Klik menu *💳 Deposit*\\.\n"
                "2\\. Pilih nominal yang Kakak inginkan\\.\n"
                "3\\. Lakukan transfer ke rekening yang tertera\\.\n"
                "4\\. Screenshot bukti transfer\\.\n"
                f"5\\. Kirim foto bukti transfer ke admin {escape_markdown(ADMIN_USERNAME)} beserta **ID Akun** Kakak\\.\n"
                "6\\. Saldo akan segera diproses oleh Admin\\!\n\n_Transaksi aman dan terpercaya 100%_ 🛡️")
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, teks, parse_mode='MarkdownV2')

    elif call.data == "menu_deposit":
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        for n in [5000, 10000, 20000, 50000]:
            markup.add(telebot.types.InlineKeyboardButton(f"Rp {n:,}", callback_data=f"depo_{n}"))
        safe_edit_message(f"Pilih nominal deposit \\(ID Anda: `{uid}`\\):", chat_id, call.message.message_id, markup)

    elif call.data.startswith("depo_"):
        d = call.data.split("_")
        if len(d) < 2: return bot.answer_callback_query(call.id, "Error nominal!")
        bot.send_message(chat_id, f"🏦 *TRANSFER MANUAL*\n\nNominal: *Rp {int(d[1]):,}*\nInfo Rekening: `{escape_markdown(BANK_ACCOUNT)}`\n\n⚠️ Harap *screenshot* bukti transfer lalu kirim ke {escape_markdown(ADMIN_USERNAME)} bersama ID Akun: `{uid}`\\.", parse_mode='MarkdownV2')

# START
resume_pending_orders()
bot.infinity_polling()
