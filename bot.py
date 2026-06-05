import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import os

# ========================================================
# KONEKSI & KONFIGURASI BOT
# ========================================================
BOT_TOKEN = '8867256199:AAHAp_rvQxiyZkT7xlYYkSo85-OrzQydv5Y'
bot = telebot.TeleBot(BOT_TOKEN)

# API Key JasaOTP 
API_KEY_OTP = os.environ.get('API_KEY_OTP', '922a0af8d090b32ee2e6114a6e572799')

# Username Telegram Admin
ADMIN_USERNAME = "@putraisalwayshappy"

# URL Dasar API Jasa OTP v1
BASE_URL_V1 = "https://api.jasaotp.id/v1/"

# ========================================================
# UTILITY FUNCTIONS
# ========================================================

def buat_pesanan_otp():
    url = f"{BASE_URL_V1}order.php"
    params = {
        'api_key': API_KEY_OTP,
        'negara': 6,
        'layanan': 'wa',
        'operator': 'any'
    }
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"Koneksi sistem terganggu: {e}"}

def cek_otp_api(order_id):
    url = f"{BASE_URL_V1}sms.php"
    params = {
        'api_key': API_KEY_OTP,
        'id': order_id
    }
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"Koneksi sistem terganggu: {e}"}

def batalkan_pesanan_api(order_id):
    url = f"{BASE_URL_V1}cancel.php"
    params = {
        'api_key': API_KEY_OTP,
        'id': order_id
    }
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"Koneksi sistem terganggu: {e}"}

# ========================================================
# HANDLER COMMANDS & CALLBACK BOT
# ========================================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    user_id = message.from_user.id
    
    # Copywriting Profesional untuk Sambutan
    text = (f"Halo, *{user_name}*! Selamat datang di **Nokos Pro Premium** ✨\n\n"
            f"Platform penyedia layanan Nomor Kosong (Nokos) otomatis, cepat, dan tepercaya untuk segala kebutuhan verifikasi aplikasi Anda.\n\n"
            f"👤 **Informasi Akun Anda:**\n"
            f"• ID Pengguna: `{user_id}`\n"
            f"• Status: Terdaftar\n\n"
            f"Silakan gunakan menu interaktif di bawah ini untuk memulai layanan kami:")
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    
    btn_server1 = InlineKeyboardButton("📱 Order WhatsApp", callback_data="order_v1")
    btn_va = InlineKeyboardButton("💳 Panduan Deposit", callback_data="info_va")
    btn_help = InlineKeyboardButton("🆘 Pusat Bantuan & Q&A", callback_data="bantuan")
    
    markup.add(btn_server1)
    markup.add(btn_va, btn_help)
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # Eksekusi Order
    if call.data == "order_v1":
        bot.answer_callback_query(call.id, "Sistem sedang menyiapkan nomor Anda...")
        res = buat_pesanan_otp()
        
        if res.get('success') == True:
            data = res.get('data', {})
            order_id = data.get('order_id')
            nomor_hp = data.get('number')
            
            pesan_sukses = (f"✅ **ORDER BERHASIL DIBUAT**\n\n"
                            f"📱 **Nomor Telepon:** `{nomor_hp}`\n"
                            f"🆔 **ID Pesanan:** `{order_id}`\n\n"
                            f"📌 **Langkah Selanjutnya:**\n"
                            f"1. Masukkan nomor di atas ke aplikasi WhatsApp.\n"
                            f"2. Kirim permintaan kode OTP dari aplikasi tersebut.\n"
                            f"3. Klik tombol **'🔄 Cek OTP'** di bawah ini secara berkala hingga kode muncul.")
            
            action_markup = InlineKeyboardMarkup()
            btn_cek = InlineKeyboardButton("🔄 Cek OTP", callback_data=f"cek_{order_id}")
            btn_cancel = InlineKeyboardButton("❌ Cancel Order (Refund)", callback_data=f"can_{order_id}")
            action_markup.add(btn_cek, btn_cancel)
            
            bot.send_message(call.message.chat.id, pesan_sukses, reply_markup=action_markup, parse_mode='Markdown')
        else:
            pesan_gagal = res.get('message', 'Mohon maaf, stok nomor sedang kosong atau saldo Anda tidak mencukupi.')
            bot.send_message(call.message.chat.id, f"❌ **ORDER GAGAL**\n\nKeterangan: {pesan_gagal}", parse_mode='Markdown')

    # Eksekusi Cek OTP
    elif call.data.startswith("cek_"):
        order_id = call.data.split("_")[1]
        bot.answer_callback_query(call.id, "Melacak pesan masuk (SMS)...")
        
        res = cek_otp_api(order_id)
        if res.get('success') == True:
            data = res.get('data', {})
            otp_code = data.get('otp')
            
            if otp_code:
                bot.send_message(call.message.chat.id, f"🎉 **KODE OTP DITEMUKAN!**\n\n🔑 Kode Verifikasi Anda: `{otp_code}`\n\n_Terima kasih telah menggunakan Nokos Pro Premium._", parse_mode='Markdown')
            else:
                bot.send_message(call.message.chat.id, f"⏳ **STATUS:** Menunggu SMS masuk.\nID Pesanan: `{order_id}`\n\n_Sistem kami sedang melacak. Silakan tunggu 15-30 detik lalu klik tombol **Cek OTP** kembali._", parse_mode='Markdown')
        else:
            pesan_gagal = res.get('message', 'Gagal memuat OTP.')
            bot.send_message(call.message.chat.id, f"⚠️ **PERHATIAN:** {pesan_gagal}", parse_mode='Markdown')

    # Eksekusi Cancel / Refund
    elif call.data.startswith("can_"):
        order_id = call.data.split("_")[1]
        bot.answer_callback_query(call.id, "Memproses pembatalan dan refund...")
        
        res = batalkan_pesanan_api(order_id)
        if res.get('success') == True:
            bot.send_message(call.message.chat.id, f"❌ **PESANAN DIBATALKAN**\n\nPesanan dengan ID `{order_id}` telah sukses dibatalkan. Saldo Anda telah otomatis dikembalikan *(Refund 100%)*.", parse_mode='Markdown')
        else:
            pesan_gagal = res.get('message', 'Pesanan tidak dapat dibatalkan (Mungkin OTP sudah terkirim atau waktu habis).')
            bot.send_message(call.message.chat.id, f"⚠️ **GAGAL DIBATALKAN:** {pesan_gagal}", parse_mode='Markdown')

    # Panduan Deposit Profesional
    elif call.data == "info_va":
        bot.answer_callback_query(call.id)
        text_va = ("💳 **PANDUAN DEPOSIT & PEMBAYARAN**\n\n"
                   "Untuk melakukan pengisian saldo, silakan ikuti panduan praktis berikut:\n\n"
                   "**Langkah 1: Lakukan Transfer**\n"
                   "Kirimkan dana sesuai nominal yang Anda inginkan ke rekening Virtual Account resmi kami:\n"
                   "🏦 **Bank Permata**\n"
                   "🔢 `{8985082065151676}` _(Klik nomor untuk menyalin otomatis)_\n\n"
                   "**Langkah 2: Simpan Bukti Pembayaran**\n"
                   "Pastikan Anda melakukan *screenshot* atau menyimpan resi transfer yang sah.\n\n"
                   "**Langkah 3: Konfirmasi ke Admin**\n"
                   f"Kirimkan bukti pembayaran Anda melalui *chat* langsung ke Admin: {ADMIN_USERNAME}.\n\n"
                   "**Langkah 4: Proses Saldo**\n"
                   "Admin akan memverifikasi mutasi Anda, dan saldo akan langsung masuk ke akun Anda dalam waktu kurang dari 5 menit.")
        bot.send_message(call.message.chat.id, text_va, parse_mode='Markdown')
        
    # Pusat Bantuan / Q&A
    elif call.data == "bantuan":
        bot.answer_callback_query(call.id)
        text_help = ("🆘 **PUSAT BANTUAN & Q&A**\n\n"
                     "**Q: Bagaimana cara kerja bot ini?**\n"
                     "A: Bot ini menyewakan nomor virtual untuk menerima SMS OTP. Anda cukup klik tombol 'Order', masukkan nomornya ke aplikasi pendaftaran, lalu klik 'Cek OTP' untuk melihat kodenya.\n\n"
                     "**Q: Berapa lama waktu tunggu SMS OTP masuk?**\n"
                     "A: Normalnya berkisar antara 10 hingga 60 detik tergantung dari *provider* aplikasi yang Anda daftarkan.\n\n"
                     "**Q: Bagaimana jika kode OTP tidak kunjung masuk?**\n"
                     "A: Jika sudah lebih dari 3 menit kode tidak masuk, silakan klik tombol **'❌ Cancel Order'**. Saldo Anda akan otomatis dikembalikan *(Refund)* ke akun Anda tanpa potongan apa pun.\n\n"
                     f"📞 **Butuh Bantuan Teknis?**\n"
                     f"Tim kami siap membantu Anda. Silakan hubungi langsung: {ADMIN_USERNAME}")
        bot.send_message(call.message.chat.id, text_help, parse_mode='Markdown')

if __name__ == "__main__":
    print("Bot Nokos Pro Premium berjalan lancar...")
    bot.infinity_polling()
