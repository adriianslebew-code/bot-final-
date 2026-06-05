import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import requests

# Konfigurasi Token dan API
# Token Bot Telegram Baru
BOT_TOKEN = '8867256199:AAHAp_rvQxiyZkT7xlYYkSo85-OrzQydv5Y'
bot = telebot.TeleBot(BOT_TOKEN)

# API Key Jasa OTP (Gunakan Environment Variable untuk keamanan di Railway)
API_KEY_JASAOTP = os.environ.get('API_KEY_JASAOTP', 'MASUKKAN_API_KEY_JASAOTP_DI_SINI')

# Konfigurasi Endpoint Jasa OTP
URL_SERVER_1 = "https://api.jasaotp.id/v1/"
URL_SERVER_2 = "https://api.jasaotp.id/v2/"

# Fungsi untuk memanggil API Saldo sebagai contoh pengecekan server
def cek_saldo(url_server):
    try:
        response = requests.get(f"{url_server}balance.php?api_key={API_KEY_JASAOTP}")
        data = response.json()
        if data.get('status'):
            return f"Rp {data.get('data', {}).get('balance', 0):,}"
        return "Gagal mengambil saldo."
    except Exception as e:
        return f"Error: {e}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    user_id = message.from_user.id
    
    # Pesan sambutan dengan formatting Markdown yang rapi
    text = (f"Halo, *{user_name}*! 👋\n\n"
            f"Selamat datang di **Bot Nokos Pro**.\n"
            f"ID Anda: `{user_id}`\n\n"
            f"Pilih layanan server di bawah ini untuk memulai order nomor kosong atau informasi top-up:")
    
    # Membuat Inline Keyboard yang terlihat estetik
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    
    # Tombol-tombol menu utama
    btn_server1 = InlineKeyboardButton("📱 Order Server 1", callback_data="order_s1")
    btn_server2 = InlineKeyboardButton("📱 Order Server 2", callback_data="order_s2")
    btn_va = InlineKeyboardButton("💳 Info VA Permata", callback_data="info_va")
    btn_help = InlineKeyboardButton("🆘 Bantuan", callback_data="bantuan")
    
    # Penempatan tata letak tombol
    markup.add(btn_server1, btn_server2)
    markup.add(btn_va)
    markup.add(btn_help)
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "order_s1":
        # Menghapus notifikasi loading di tombol
        bot.answer_callback_query(call.id)
        
        # Contoh eksekusi endpoint API Server 1
        text_s1 = (f"🌐 **SERVER 1 AKTIF**\n\n"
                   f"Endpoint: `{URL_SERVER_1}order.php`\n"
                   f"Status: Siap menerima order.\n\n"
                   f"_Silakan ketik kode layanan yang ingin diorder_ (Fitur masih dalam tahap pengembangan visual).")
        bot.send_message(call.message.chat.id, text_s1, parse_mode='Markdown')

    elif call.data == "order_s2":
        bot.answer_callback_query(call.id)
        
        # Contoh eksekusi endpoint API Server 2
        text_s2 = (f"🌐 **SERVER 2 AKTIF**\n\n"
                   f"Endpoint: `{URL_SERVER_2}order.php`\n"
                   f"Status: Siap menerima order.\n\n"
                   f"_Silakan ketik kode layanan yang ingin diorder_ (Fitur masih dalam tahap pengembangan visual).")
        bot.send_message(call.message.chat.id, text_s2, parse_mode='Markdown')

    elif call.data == "info_va":
        bot.answer_callback_query(call.id)
        text_va = ("🏦 **Informasi Pembayaran / Top Up**\n\n"
                   "Silakan transfer ke rekening Virtual Account berikut:\n\n"
                   "**Bank Permata**\n"
                   "`8985082065151676`\n\n"
                   "_(Klik nomor di atas untuk menyalin otomatis)_")
        bot.send_message(call.message.chat.id, text_va, parse_mode='Markdown')
        
    elif call.data == "bantuan":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Jika Anda mengalami kendala saat order atau API lambat merespons, silakan hubungi admin.", parse_mode='Markdown')

# Memastikan bot berjalan terus-menerus
if __name__ == "__main__":
    print("Bot Nokos Pro sedang berjalan...")
    bot.infinity_polling()
