import os
import dotenv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import json
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Load token dari file .env
dotenv.load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


class GraphBot:
    def __init__(self, token):
        self.app = Application.builder().token(token).build()
        self.chat_analyzer = ChatAnalyzer()

        # Menambahkan command dan message handler
        self.app.add_handler(CommandHandler("grafik", self.send_graph))
        self.app.add_handler(CommandHandler("count_test", self.send_test_count))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.store_message))

    def generate_graph(self, file_path="grafik.png"):
        """Membuat dan menyimpan grafik aktivitas dalam satu bulan terakhir."""
        today = datetime.datetime.today()
        dates = [today - datetime.timedelta(days=i) for i in range(5)]
        dates.reverse()
        y_values = [10, 20, 15, 25, 30]

        plt.figure(figsize=(16, 10))
        plt.plot(dates, y_values, marker='o', linestyle='-')
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d-%m"))

        plt.title("Grafik Aktivitas Fixed Jib Crane")
        plt.xlabel("Tanggal")
        plt.ylabel("Jumlah Aktivitas")

        plt.savefig(file_path)
        plt.close()

    async def send_graph(self, update: Update, context: CallbackContext):
        """Mengirim grafik ke pengguna."""
        file_path = "grafik.png"
        self.generate_graph(file_path)

        with open(file_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)

    async def store_message(self, update: Update, context: CallbackContext):
        """Menyimpan pesan yang dikirim oleh bot atau pesan yang mereply bot."""
        user = update.effective_user
        message = update.message
        timestamp = datetime.datetime.now()

        print(f"User ID: {user.id}, is_bot: {user.is_bot}")

        # Menyimpan pesan bot itu sendiri
        if user.is_bot:
            print(f"[BOT MESSAGE] Menyimpan pesan bot: {message.text} pada {timestamp}")
            self.chat_analyzer.add_chat(user.id, message.text, timestamp)

        # Menangkap pesan yang merupakan reply terhadap bot
        elif message.reply_to_message and message.reply_to_message.from_user.is_bot:
            bot_message_text = message.reply_to_message.text  # Pesan bot yang direply
            reply_text = message.text  # Balasan dari user

            print(f"[REPLY TO BOT] Pesan bot yang direply: {bot_message_text}")
            print(f"[REPLY] User membalas: {reply_text} pada {timestamp}")

            # Simpan pesan bot dan balasan user
            self.chat_analyzer.add_chat(user.id, f"REPLY: {bot_message_text} -> {reply_text}", timestamp)

    async def send_test_count(self, update: Update, context: CallbackContext):
        """Mengirim jumlah pesan 'test' dari bot bulan ini."""
        bot_id = update.effective_user.id
        test_counts = self.chat_analyzer.count_test_messages(bot_id)

        if not test_counts:
            await update.message.reply_text("Tidak ada pesan 'test' bulan ini.")
            return
        
        response = "\n".join([f"{date.strftime('%d-%m')} = {count}" for date, count in test_counts.items()])
        await update.message.reply_text(f"Jumlah chat 'test' bulan ini:\n{response}")

    def run(self):
        """Menjalankan bot."""
        print("Bot is running...")
        self.app.run_polling(drop_pending_updates=False)  # Agar bot bisa membaca pesan sendiri

class ChatAnalyzer:
    def __init__(self, file_path=DATA_FILE):
        self.file_path = file_path
        self.chats = self.load_data()
    
    def load_data(self):
        """Memuat data chat dari file JSON."""
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                return json.load(f)
        return defaultdict(list)

    def save_data(self):
        """Menyimpan data chat ke file JSON."""
        with open(self.file_path, "w") as f:
            json.dump(self.chats, f, default=str)

    def add_chat(self, user_id: int, message: str, timestamp: datetime.datetime):
        """Menambahkan chat ke dalam penyimpanan."""
        self.chats[str(user_id)].append((message, timestamp.isoformat()))
        self.save_data()
    
    def count_test_messages(self, bot_id: int):
        """Menghitung jumlah pesan 'test' dari bot dalam bulan ini."""
        now = datetime.datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        test_counts = defaultdict(int)

        for msg, time in self.chats.get(str(bot_id), []):
            time = datetime.datetime.fromisoformat(time)
            if msg.lower() == "test" and time >= start_of_month:
                test_counts[time.date()] += 1
        
        return test_counts

if __name__ == "__main__":
    if TOKEN:
        bot = GraphBot(TOKEN)
        bot.run()
    else:
        print("Error: Token tidak ditemukan. Pastikan file .env sudah dikonfigurasi dengan benar.")
