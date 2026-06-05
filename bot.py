import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests

# Konfigurasi Bot
BOT_TOKEN = "8341181663:AAG4a_EVeF5Lw1K3Kdj1j5Zn35eKJS643tw"
API_KEY_OTP = "136931718169904207945638210331464426570643606"
ADMIN_CODE = "2705"

bot = telebot.TeleBot(BOT_TOKEN)

def request_api(server, endpoint, params=None):
    base_url = f"https://api.jasaotp.id/v{server}/"
    params = params or {}
    params['api_key'] = API_KEY_OTP
    try:
        response = requests.get(base_url + endpoint, params=params, timeout=10)
        return response.json()
    except:
        return {"code": 500, "message": "Server tidak merespons"}

@bot.message_handler(func=lambda message: message.text == ADMIN_CODE)
def admin_panel(message):
    saldo = request_api(1, "balance.php", {})
    saldo_info = f"Rp {saldo['data']['saldo']:,}" if saldo and saldo.get("success") else "Gagal Cek"
    bot.reply_to(message, f"🛠 *PANEL ADMIN*\n\n💰 Saldo API: *{saldo_info}*", parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📱 Order Server 1", callback_data="order_1"),
               InlineKeyboardButton("📱 Order Server 2", callback_data="order_2"))
    markup.add(InlineKeyboardButton("💳 Info VA Permata", callback_data="topup"))
    bot.send_message(message.chat.id, "Selamat datang di Bot Nokos Pro!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    data = call.data
    
    if data.startswith("order_"):
        server = 1 if data == "order_1" else 2
        hasil = request_api(server, "order.php", {"negara": 6, "layanan": "wa", "operator": "any"})
        if hasil and hasil.get("success"):
            oid = hasil['data']['order_id']
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔍 Cek OTP", callback_data=f"cek_{server}_{oid}"))
            markup.add(InlineKeyboardButton("❌ Refund", callback_data=f"cancel_{server}_{oid}"))
            bot.send_message(chat_id, f"✅ Order Berhasil!\nID: `{oid}`\nNomor: `{hasil['data']['number']}`", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ {hasil.get('message', 'Error')}")
            
    elif data.startswith("cek_"):
        _, server, oid = data.split("_")
        hasil = request_api(server, "sms.php", {"id": oid})
        bot.reply_to(call.message, f"✨ OTP: `{hasil['data']['otp']}`" if hasil and hasil.get("success") else "⏳ Belum ada SMS.")
        
    elif data.startswith("cancel_"):
        _, server, oid = data.split("_")
        hasil = request_api(server, "cancel.php", {"id": oid})
        bot.reply_to(call.message, "✅ Refund Berhasil." if hasil and hasil.get("success") else "❌ Gagal refund.")
        
    elif data == "topup":
        bot.send_message(chat_id, "🏦 Transfer ke VA Permata: `8985082065151676`", parse_mode="Markdown")

bot.infinity_polling()
