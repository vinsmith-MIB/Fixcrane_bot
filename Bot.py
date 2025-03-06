import os
import shutil
import dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from Chart import Chart
from File import File

# Load token dari file .env
dotenv.load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


class Bot:
    def __init__(self):
        self.app = Application.builder().token(TOKEN).build()
        
        # Menambahkan command dan message handler
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.download_file))
        self.app.add_handler(CommandHandler("chart", self.send_chart))  # Tambahkan command handler untuk /chart

    async def download_file(self, update: Update, context: CallbackContext):
        """Menerima dokumen dan mengunduhnya."""
        document = update.message.document
        file_id = document.file_id

        # Mendapatkan file dari server Telegram
        file = await context.bot.get_file(file_id)

        # Simpan file ke lokal
        file_name = document.file_name if document.file_name else "downloaded_file"
        save_path = os.path.join("downloads", file_name)

        os.makedirs("downloads", exist_ok=True)  # Buat folder jika belum ada

        await file.download_to_drive(save_path)
        await update.message.reply_text(f"File telah diunduh: {file_name}")
        await update.message.reply_text('Tunggu sebentar...')

        # Ekstrak dan proses file
        File.extract_rar()
        File.folder_iteration()
        await self.send_chart(update, context)


    async def send_chart(self, update: Update, context: CallbackContext):
        """Mengirimkan seluruh folder grafik dalam bentuk ZIP ke pengguna."""
        chat_id = update.message.chat_id
        folder_path = "grafik"
        zip_path = "grafik.zip"

        if not os.path.exists(folder_path):
            await update.message.reply_text("Folder grafik tidak ditemukan.")
            return

        # Kompres folder grafik menjadi ZIP
        shutil.make_archive("grafik", "zip", folder_path)

        # Kirim file ZIP ke pengguna
        with open(zip_path, "rb") as file:
            await context.bot.send_document(chat_id, document=file, filename="grafik.zip")

        # Hapus file ZIP setelah dikirim untuk menghemat penyimpanan
        os.remove(zip_path)
        
        for folder in ["grafik", "downloads", "hasil_ekstrak"]:
            if os.path.exists(folder):
                shutil.rmtree(folder)

        await update.message.reply_text("📂 Folder grafik telah dikirim dalam bentuk ZIP!")

    def run(self):
        """Menjalankan bot."""
        print("Bot sedang berjalan...")
        self.app.run_polling()

