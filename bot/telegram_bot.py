# bot/telegram_bot.py

from collections import defaultdict
import os
import re
import telegram
import asyncio
import json
import math
import uuid
import calendar
from datetime import date, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)
from telegram.error import TimedOut, RetryAfter
from bot.bot_config import BOT_TOKEN, DB_CONFIG
from services.rar_parser_service import RarParserService
from services.zip_parser_service import ZipParserService
from services.maintenance_service import MaintenanceService
from services.graph_service import GraphService
from database.db_manager import DBManager
from database.models import MaintenanceRecord, FaultReference
from bot.admin_auth import admin_only, is_admin
import logging

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================
#  INITIALIZATION
# ==============================
print("Menginisialisasi services...")
db_manager = DBManager(DB_CONFIG)
maintenance_service = MaintenanceService(db_manager)
rar_parser_service = RarParserService(maintenance_service)
zip_parser_service = ZipParserService(maintenance_service)
graph_service = GraphService(maintenance_service)

class TelegramBot:
    def __init__(self, token, maintenance_service):
        print("Inisialisasi TelegramBot...")
        self.token = token
        self.maintenance_service = maintenance_service
        self.rar_parser_service = rar_parser_service
        self.zip_parser_service = zip_parser_service
        self.application = ApplicationBuilder() \
            .token(token) \
            .read_timeout(7) \
            .get_updates_read_timeout(42) \
            .build()
        self._re_data = re.compile(r"^(all|\d+)\s+(\d{2}-\d{2}-\d{4})\s+(\d{2}-\d{2}-\d{4})\s+(all|\d+|.+)$")
        self.setup_handlers()

    # ==============================
    #  HANDLER SETUP
    # ==============================
    def setup_handlers(self):
        print("Men-setup handlers...")
        handlers = [
            CommandHandler("start", self.start),
            CommandHandler("grafik", self.handle_graph_command),
            CommandHandler("data", self.handle_data_command),
            CommandHandler("hapus", self.admin_delete),
            CommandHandler("id", self.get_user_id),
            MessageHandler(filters.Document.ALL, self.handle_document),
            CallbackQueryHandler(self.update_callback_query)
        ]
        for handler in handlers:
            self.application.add_handler(handler)
    

    # ==============================
    #  USER ID
    # ==============================
    async def get_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Berikan user ID mereka"""
        user_id = update.effective_user.id
        await update.message.reply_text(f"👤 User ID Anda: `{user_id}`\n\n"
                                    "Berikan ID ini ke admin untuk ditambahkan ke ADMIN_USER_IDS",
                                    parse_mode=telegram.constants.ParseMode.MARKDOWN)
    # ==============================
    #  COMMAND HANDLERS
    # ==============================
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with main menu"""
        keyboard = [
            [InlineKeyboardButton("📊 Lihat Grafik", callback_data='show_graph')],
            [InlineKeyboardButton("📋 Lihat Data", callback_data='show_data')],
            [InlineKeyboardButton("🗑️ Hapus Data", callback_data='delete_data')],
            [InlineKeyboardButton("❓ Cara Penggunaan", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Halo!\n\nSilakan pilih fitur di bawah ini:", reply_markup=reply_markup)
    
    async def handle_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /data command"""
        await self.query_handler(update, context, "show_data")

    async def handle_graph_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /grafik command"""
        await self.query_handler(update, context, "show_graph")
    
    async def handle_delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /hapus command"""
        await self.query_handler(update, context, "delete_data")

    # ==============================
    #  QUERY PROCESSING
    # ==============================
    async def query_handler(self, update, context, query_func):
        args = context.args
        text = " ".join(args)

        # Jika tidak ada argumen sama sekali (/grafik), mulai alur interaktif
        if not text:
            await self.crane_button_handler(update, context, query_func)
            return

        # Coba cocokkan dengan format perintah lengkap terlebih dahulu
        match = self._re_data.match(text)
        if match:
            # Jika cocok, proses seperti biasa
            crane_input, start_date_str, end_date_str, fault_input = match.groups()
            try:
                start_date_obj = datetime.strptime(start_date_str, "%d-%m-%Y")
                end_date_obj = datetime.strptime(end_date_str, "%d-%m-%Y")
                if start_date_obj > end_date_obj:
                    await update.message.reply_text("❌ Tanggal mulai tidak boleh setelah tanggal akhir")
                    return
                start_date = start_date_obj.strftime("%Y-%m-%d")
                end_date = end_date_obj.strftime("%Y-%m-%d")
            except ValueError:
                await update.message.reply_text("❌ Format tanggal salah. Gunakan format DD-MM-YYYY")
                return
            
            # Logika handling berdasarkan input (all/spesifik)
            if crane_input == "all" and fault_input == "all":
                records = self.maintenance_service.get_all_records_by_date_range(start_date, end_date)
                await self.handle_bulk_action(update, context, query_func, records, start_date, end_date, "all", "all")
            elif crane_input == "all":
                matches = self.maintenance_service.search_faults_by_keyword(fault_input)
                if len(matches) == 1:
                    records = self.maintenance_service.get_all_records_by_date_and_fault(start_date, end_date, matches[0].fault_id)
                    await self.handle_bulk_action(update, context, query_func, records, start_date, end_date, "all", matches[0].fault_id)
                else:
                    await self.handle_fault_selection(update, context, query_func, "all", start_date, end_date, fault_input)
            elif fault_input == "all":
                records = self.maintenance_service.get_all_records_by_date_and_crane(start_date, end_date, crane_input)
                await self.handle_bulk_action(update, context, query_func, records, start_date, end_date, crane_input, "all")
            else:
                matches = self.maintenance_service.search_faults_by_keyword(fault_input)
                if len(matches) == 1:
                    records = self.maintenance_service.get_records_by_date_and_id_crane_and_id_fault(
                        start_date, end_date, crane_input, matches[0].fault_id)
                    await self.handle_bulk_action(update, context, query_func, records, start_date, end_date, crane_input, matches[0].fault_id)
                else:
                    await self.handle_fault_selection(update, context, query_func, crane_input, start_date, end_date, fault_input)
            return

        # --- LOGIKA BARU: Alur Interaktif untuk Perintah Parsial ---
        num_args = len(args)
        crane_input = args[0]

        # Kasus: /grafik [crane] -> Tampilkan pilihan tahun
        if num_args == 1:
            callback_data_mimic = f"{query_func}|{crane_input}"
            await self.year_button_handler(update, context, crane_input, callback_data_mimic)
            return

        # Kasus: /grafik [crane] [start_date] [end_date] -> Tampilkan pilihan fault
        if num_args == 3:
            try:
                start_date_obj = datetime.strptime(args[1], "%d-%m-%Y")
                end_date_obj = datetime.strptime(args[2], "%d-%m-%Y")
                
                if start_date_obj > end_date_obj:
                    await update.message.reply_text("❌ Tanggal mulai tidak boleh setelah tanggal akhir")
                    return
                    
                start_date = start_date_obj.strftime("%Y-%m-%d")
                end_date = end_date_obj.strftime("%Y-%m-%d")
                
                # Lanjutkan ke pemilihan fault
                callback_data_mimic = f"{query_func}|{crane_input}|{start_date}|{end_date}"
                await self.fault_button_handler(update, context, callback_data_mimic, page=1)
                return

            except (ValueError, IndexError):
                # Jika tanggal tidak valid, jangan lanjutkan
                await update.message.reply_text("Format tanggal salah. Gunakan DD-MM-YYYY.")
                return
        
        # Jika format tidak cocok sama sekali (misal: 2 arg, atau 3 arg dengan format salah)
        await update.message.reply_text(
            "Format perintah tidak lengkap. Silakan gunakan tombol atau format lengkap:\n"
            "`/grafik [crane] [dd-mm-yyyy] [dd-mm-yyyy] [fault]`",
            parse_mode=telegram.constants.ParseMode.MARKDOWN
        )
    
    async def handle_bulk_action(self, update, context, action, records, start_date, end_date, crane_id, fault_id):
        print(f"Handling bulk action: {action} for crane {crane_id}, fault {fault_id}, records count: {len(records)}")
        # Batasi operasi bulk maksimal 500 record
        if len(records) > 500000000:
            await update.message.reply_text("⚠️ Operasi bulk terbatas untuk 500 record maksimal. Silakan persempit rentang waktu atau kriteria.")
            return
        
        if not records:
            await update.message.reply_text("❌ Tidak ada data ditemukan.")
            return
        
        if action == "show_data":
            await self.show_bulk_data(update, records)
        elif action == "show_graph":
            await self.show_graph(update, context, records, start_date, end_date)
        elif action == "delete_data":
            await self.delete_bulk_confirmation(update, context, records, crane_id, start_date, end_date, fault_id)

    async def handle_fault_selection(self, update, context, query_func, crane_id, start_date, end_date, fault_input):
        matches = self.maintenance_service.search_faults_by_keyword(fault_input)
        if not matches:
            await update.message.reply_text(f"❌ Tidak ditemukan fault '{fault_input}'.")
            return
        
        keyboard = []
        for fault in matches[:10]:
            cb_data = f"{query_func}|{crane_id}|{start_date}|{end_date}|{fault.fault_id}"
            keyboard.append([InlineKeyboardButton(f"{fault.code_fault}-{fault.fault_name}", callback_data=cb_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Pilih fault:", reply_markup=reply_markup)

    # ==============================
    #  DATA DISPLAY METHODS
    # ==============================
    async def show_bulk_data(self, update, records):
        # Group by crane dan fault untuk summary
        summary = {}
        for r in records:
            key = f"fc0{r.crane_id}|{r.fault_reference.fault_name}"
            summary[key] = summary.get(key, 0) + 1
        
        # Format compact
        text = f"📊 **SUMMARY DATA ({len(records)} total)**\n\n"
        for key, count in sorted(summary.items())[:20]:
            crane, fault = key.split("|", 1)
            text += f"`{crane}` {fault[:30]}{'...' if len(fault)>30 else ''}: **{count}**\n"
        
        if len(summary) > 20:
            text += f"\n...dan {len(summary)-20} fault lainnya"
        
        # Sample data (5 records)
        text += f"\n\n📋 **SAMPLE DATA (5/{len(records)})**\n```json\n"
        sample = []
        for r in records[:5]:
            sample.append({
                "tanggal": r.tanggal.isoformat(),
                "crane": f"fc0{r.crane_id}",
                "fault": r.fault_reference.fault_name,
                "act": r.act
            })
        text += json.dumps(sample, indent=1, ensure_ascii=False)[:1500] + "```"
        
        await update.message.reply_text(text, parse_mode=telegram.constants.ParseMode.MARKDOWN)

    async def show_data(self, update, records: list[MaintenanceRecord]):
        if not records:
            text = "❌ Tidak ada data untuk fault pada periode tersebut."
            print("Data kosong:", text)
        else:
            def serialize_row(row):
                serialized_data = {}
                for attribute_name, attribute_value in row.__dict__.items():
                    if attribute_name.startswith('_'):
                        continue  # Skip internal SQLAlchemy attributes
                    if isinstance(attribute_value, date):
                        serialized_data[attribute_name] = attribute_value.isoformat()
                    elif isinstance(attribute_value, FaultReference):
                        serialized_data[attribute_name] = {
                            'fault_id': attribute_value.fault_id,
                            'fault_name': attribute_value.fault_name,
                            'code_fault': attribute_value.code_fault
                        }
                    else:
                        serialized_data[attribute_name] = attribute_value
                return serialized_data

            serialized = [serialize_row(row) for row in records[:20]]
            json_data = json.dumps(serialized, indent=2, ensure_ascii=False)
            text = f"📄 Ditemukan {len(records)} data:\n\n```json\n{json_data}\n```"
            
            if len(text) > 4000:
                text = text[:3990] + "\n...lanjutnya data terpotong.```"

        if isinstance(update, telegram.Update):
            try:
                await update.message.reply_text(text, parse_mode=telegram.constants.ParseMode.MARKDOWN)
            except Exception as e:
                print("Error saat mengirim pesan:", e)
        else:
            try:
                await update.edit_message_text(text, parse_mode=telegram.constants.ParseMode.MARKDOWN)
            except Exception as e:
                print("Error saat mengedit pesan:", e)

    # ==============================
    #  GRAPH HANDLING
    # ==============================
    async def show_graph(self, update_or_query, context, records, start_date, end_date):
        logger.info(f"Starting graph generation for {len(records)} records")
        grouped_records = defaultdict(list)
        for record in records:
            key = f"{record.crane_id}|{record.fault_name}"
            grouped_records[key].append(record)

        logger.info(f"Grouped records into {len(grouped_records)} groups")

        for key, group in grouped_records.items():
            logger.info(f"Processing graph for group: {key} with {len(group)} records")
            try:
                if isinstance(update_or_query, Update):
                    chat_id = update_or_query.effective_chat.id
                else:
                    chat_id = update_or_query.message.chat_id

                loading_message = await context.bot.send_message(chat_id=chat_id, text="📊 Sedang memproses grafik... Mohon tunggu.")
                logger.info(f"Sent loading message for chat_id: {chat_id}")

                logger.info(f"Calling graph_service.generate_graph for key: {key}")
                file_path = await asyncio.to_thread(
                    graph_service.generate_graph, 
                    group, 
                    start_date, 
                    end_date,
                    key
                )
                logger.info(f"Graph generation completed. File path: {file_path}")

                if file_path and os.path.exists(file_path):
                    logger.info(f"Graph file exists at: {file_path}")
                    with open(file_path, "rb") as photo:
                        sent = False
                        while not sent:
                            try:
                                await context.bot.send_photo(chat_id=chat_id, photo=photo)
                                sent = True
                                logger.info(f"Successfully sent graph for key: {key}")
                            except RetryAfter as e:
                                wait = getattr(e, "retry_after", 5)
                                logger.warning(f"Flood control, retry after {wait}s")
                                await asyncio.sleep(wait)
                    
                    await context.bot.delete_message(chat_id=chat_id, message_id=loading_message.message_id)
                    try:
                        os.remove(file_path)
                        logger.info(f"Cleaned up graph file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove graph file: {e}")
                else:
                    logger.warning(f"Graph file not found or empty: {file_path}")
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=loading_message.message_id,
                        text="⚠️ Grafik gagal dibuat: tidak ada data maintenance pada rentang tanggal tersebut."
                    )

                # Tambahkan delay antar pengiriman gambar jika perlu
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error saat membuat grafik untuk key {key}:", exc_info=True)
                try:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Terjadi kesalahan saat membuat grafik: {e}")
                except Exception as send_error:
                    logger.error(f"Failed to send error message: {send_error}")

    # ==============================
    #  DELETE OPERATIONS
    # ==============================
    @admin_only
    async def admin_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk /hapus yang sudah diproteksi"""
        await self.query_handler(update, context, "delete_data")
        
    async def delete_bulk_confirmation(self, update, context, records, crane_id, start_date, end_date, fault_id):
        count = len(records)
        start_display = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        end_display = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        
        crane_text = "ALL CRANES" if crane_id == "all" else f"fc0{crane_id}"
        fault_text = "ALL FAULTS" if fault_id == "all" else records[0].fault_reference.fault_name
        
        text = f"⚠️ **BULK DELETE CONFIRMATION**\n\n🏗️{crane_text}\n📅{start_display}-{end_display}\n🔧{fault_text}\n📊**{count} RECORDS**\n\n❗**IRREVERSIBLE!**"
        
        keyboard = [[
            InlineKeyboardButton("✅DELETE", callback_data=f"bulk_delete|{crane_id}|{start_date}|{end_date}|{fault_id}"),
            InlineKeyboardButton("❌CANCEL", callback_data="cancel_delete")
        ]]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=telegram.constants.ParseMode.MARKDOWN)
    
    async def execute_bulk_delete(self, update, context, crane_id, start_date, end_date, fault_id):
        try:
            loading = await update.callback_query.edit_message_text("🗑️ Deleting...")
            
            if crane_id == "all" and fault_id == "all":
                deleted = self.maintenance_service.delete_all_records_by_date_range(start_date, end_date)
            elif crane_id == "all":
                deleted = self.maintenance_service.delete_all_records_by_date_and_fault(start_date, end_date, fault_id)
            elif fault_id == "all":
                deleted = self.maintenance_service.delete_all_records_by_crane_and_date_range(crane_id, start_date, end_date)
            else:
                deleted = self.maintenance_service.delete_records_by_date_and_id_crane_and_id_fault(start_date, end_date, crane_id, fault_id)
            
            start_display = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            end_display = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            
            text = f"✅ **DELETED {deleted} RECORDS**\n📅{start_display}-{end_display}\n🕒{datetime.now().strftime('%H:%M:%S')}"
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=loading.message_id, text=text, parse_mode=telegram.constants.ParseMode.MARKDOWN)
            
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Error: {e}")
            
    async def execute_delete_data(self, update, context, crane_id, start_date, end_date, fault_id):
        """Menjalankan penghapusan data setelah konfirmasi"""
        try:
            chat_id = update.effective_chat.id
            
            # Kirim pesan loading
            loading_message = await update.callback_query.edit_message_text("🗑️ Sedang menghapus data... Mohon tunggu.")
            
            # Dapatkan records yang akan dihapus untuk menghitung jumlahnya
            records_to_delete = self.maintenance_service.get_records_by_date_and_id_crane_and_id_fault(
                start_date, end_date, crane_id, fault_id
            )
            
            if not records_to_delete:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=loading_message.message_id,
                    text="❌ Tidak ada data yang dapat dihapus."
                )
                return
            
            record_count = len(records_to_delete)
            
            # Lakukan penghapusan data
            deleted_count = self.maintenance_service.delete_records_by_date_and_id_crane_and_id_fault(
                start_date, end_date, crane_id, fault_id
            )
            
            # Format tanggal untuk tampilan
            start_display = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            end_display = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            
            # Dapatkan informasi fault
            fault_info = records_to_delete[0].fault_reference if records_to_delete else None
            fault_name = fault_info.fault_name if fault_info else "Unknown"
            
            success_text = (
                f"✅ **DATA BERHASIL DIHAPUS**\n\n"
                f"📍 **Crane:** fc0{crane_id}\n"
                f"📅 **Periode:** {start_display} - {end_display}\n"
                f"🔧 **Fault:** {fault_name}\n"
                f"📊 **Jumlah Data Terhapus:** {deleted_count} record\n\n"
                f"🕒 **Waktu:** {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
            )
            
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=loading_message.message_id,
                text=success_text,
                parse_mode=telegram.constants.ParseMode.MARKDOWN
            )
            
            print(f"Data berhasil dihapus: {deleted_count} records untuk crane {crane_id}, fault {fault_id}")
            
        except Exception as e:
            print(f"Terjadi kesalahan saat menghapus data: {e}")
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=loading_message.message_id,
                    text=f"❌ Terjadi kesalahan saat menghapus data: {e}"
                )
            except:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Terjadi kesalahan saat menghapus data: {e}")

    # ==============================
    #  CALLBACK HANDLING
    # ==============================
    async def update_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            callback_query = update.callback_query
            await callback_query.answer()
            query_data = callback_query.data
            print(f"Received callback query: {query_data}")
            
            if query_data.startswith("bulk_delete|"):
                user_id = update.effective_user.id
                if not is_admin(user_id):
                    await callback_query.edit_message_text(
                        "⛔ *PERINGATAN: Akses Ditolak!*\n\n"
                        "Aksi penghapusan hanya dapat dilakukan oleh admin.\n\n"
                        f"User ID Anda: `{user_id}`\n"
                        "Hubungi admin untuk ditambahkan ke sistem",
                        parse_mode=telegram.constants.ParseMode.MARKDOWN
                    )
                    return
                parts = query_data.split("|")
                if len(parts) == 5:
                    _, crane_id, start_date, end_date, fault_id = parts
                    await self.execute_bulk_delete(update, context, crane_id, start_date, end_date, fault_id)
                    return
            elif query_data.startswith("confirm_delete|"):
                parts = query_data.split("|")
                if len(parts) == 5:
                    _, crane_id, start_date, end_date, fault_id = parts
                    await self.execute_delete_data(update, context, crane_id, start_date, end_date, fault_id)
                    return
            elif query_data == "cancel_delete":
                await callback_query.edit_message_text("❌ Cancelled.")
                return
            
            await callback_query.edit_message_reply_markup(reply_markup=None)
            await self.handle_buttons(update, context, query_data)
        except Exception as e:
            logger.error("Error pada callback query:", exc_info=True)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Terjadi kesalahan saat memproses permintaan"
            )

    async def handle_buttons(self, update, context, query):
        parts = query.split("|")
        
        if len(parts) == 5:
            action, crane_id, start_date, end_date, fault = parts
            
            if parts[-1].startswith("page="):
                page = int(parts[4].split("=")[1])
                return await self.fault_button_handler(update, context, "|".join(parts[:4]), page)

            records = self.maintenance_service.get_records_by_date_and_id_crane_and_id_fault(
            start_date, end_date, crane_id, fault
            )
            # Periksa jika records kosong
            if not records:
                return await update.callback_query.edit_message_text("❌ Tidak ada data ditemukan untuk fault tersebut.")

            # Memproses aksi
            if action == "show_data":
                await self.show_data(update, records)
            elif action == "show_graph":
                await self.show_graph(update, context, records, start_date, end_date)
            elif action == "delete_data":
                return
            else:
                await update.edit_message_text("❌ Aksi callback tidak dikenali.")
                
        # 4) action|crane_id|start_YYYY-MM|end_YYYY-MM — tampilkan pilihan fault
        elif len(parts) == 4:
            action, crane_id, start_raw, end_raw = parts
            # Normalisasi tanggal: start = tgl 01, end = tgl terakhir bulan
            try:
                # start_raw/end_raw format: YYYY-MM-DD
                start_dt = datetime.strptime(start_raw, "%Y-%m-%d")
                end_dt = datetime.strptime(end_raw, "%Y-%m-%d")
                # Set tanggal 1 untuk start
                start_date = start_dt.replace(day=1).strftime("%Y-%m-%d")
                # Set tanggal terakhir untuk end
                last_day = calendar.monthrange(end_dt.year, end_dt.month)[1]
                end_date = end_dt.replace(day=last_day).strftime("%Y-%m-%d")
                # Lanjutkan ke fault_button_handler dengan parts yang sudah dinormalisasi
                new_query = f"{action}|{crane_id}|{start_date}|{end_date}"
                return await self.fault_button_handler(update, context, new_query, 1)
            except Exception as e:
                print(f"Error normalisasi tanggal: {e}")
                return await self.month_button_handler(update, context, query)
        
        # 3) action|crane_id|start_YYYY-MM — tampilkan pilihan end YYYY-MM
        elif len(parts) == 3:
            action, crane_id, _ = parts
            date_query_match = re.compile(r"(\d{4}-\d{2})")
            date_match       = date_query_match.match(parts[-1])
            if date_match:
                return await self.year_button_handler(update, context, crane_id, query)
            else:
                return await self.month_button_handler(update, context, query)
        
        # 2) action|crane_id — tampilkan pilihan start YYYY-MM
        elif len(parts) == 2:
            action, crane_id = parts
            return await self.year_button_handler(update, context, crane_id, query)
        
        elif len(parts) == 1:
            if parts[0] == "help":
                help_text = (
                "🛠️ *Cara Penggunaan Bot Maintenance Crane*\n\n"
                "1. *Menu Utama* - Ketik /start untuk menampilkan menu utama dengan pilihan:\n"
                "   - 📊 Lihat Grafik: Menampilkan grafik frekuensi maintenance\n"
                "   - 📋 Lihat Data: Menampilkan data maintenance dalam format JSON\n"
                "   - 🗑️ Hapus Data: Menghapus data maintenance (dengan konfirmasi)\n"
                "   - ❓ Cara Penggunaan: Menampilkan panduan ini\n\n"
                
                "2. *Melihat Data Maintenance* - Gunakan perintah:\n"
                "   `/data <crane_id> <start_date> <end_date> <fault_keyword>`\n"
                "   Contoh: `/data 1 01-03-2024 31-03-2024 175`\n\n"
                
                "3. *Melihat Grafik* - Gunakan perintah:\n"
                "   `/grafik <crane_id> <start_date> <end_date> <fault_keyword>`\n"
                "   Contoh: `/grafik 2 01-01-2024 31-01-2024 Brake`\n\n"
                
                "4. *Menghapus Data* - Gunakan perintah:\n"
                "   `/hapus <crane_id> <start_date> <end_date> <fault_keyword>`\n"
                "   Contoh: `/hapus 1 01-03-2024 31-03-2024 175`\n"
                "   ⚠️ *Perhatian:* Data yang dihapus tidak dapat dikembalikan!\n\n"
                
                "5. *Mode Interaktif* - Tanpa perintah:\n"
                "   - Pilih crane → tahun → bulan → fault\n"
                "   - Bot akan memandu Anda langkah demi langkah\n\n"
                
                "6. *Upload Data* - Kirim file berupa:\n"
                "   - ZIP/RAR berisi laporan maintenance (.csv)\n"
                "   - File EventLib.csv langsung\n\n"
                
                "⚠️ *Catatan Penting:*\n"
                "- Format tanggal: DD-MM-YYYY (contoh: 15-03-2024)\n"
                "- Data ditampilkan maksimal 20 record sekaligus\n"
                "- Penghapusan data memerlukan konfirmasi\n"
                "- Grafik membutuhkan waktu proses 10-30 detik\n\n"
                "🔧 Masalah teknis? Hubungi admin @username"
                )
                await update.callback_query.edit_message_text(
                    help_text,
                    parse_mode=telegram.constants.ParseMode.MARKDOWN
                )
            else:
                return await self.crane_button_handler(update, context, parts[0])

    # ==============================
    #  BUTTON HANDLERS
    # ==============================
    async def crane_button_handler(self, update, context, action):
        rows = self.maintenance_service.get_all_crane_id()
        cranes = sorted({r['crane_id'] for r in rows})
        keyboard = [
            [InlineKeyboardButton(f"fc0{c}", callback_data=f"{action}|{c}")]
            for c in cranes
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                "📌 Pilih Crane:", reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "📌 Pilih Crane:", reply_markup=reply_markup
            )

    async def year_button_handler(self, update, context, crane_id, parts):
        rows = self.maintenance_service.get_all_year(crane_id)
        opts = sorted({f"{r['tahun']}" for r in rows })
        keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"{parts}|{opt}")]
        for opt in opts
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                "📌 Pilih Tahun:", reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "📌 Pilih Tahun :", reply_markup=reply_markup
            )
        
    async def month_button_handler(self, update, context, parts):
        try:
            year = None
            parts_split = parts.split("|")
            for p in reversed(parts_split):
                if p.isdigit() and len(p) == 4:
                    year = int(p)
                    break
            if year is None:
                year = datetime.now().year
        except Exception:
            year = datetime.now().year

        opts = [i for i in range(1, 13)]
        keyboard = []
        row = []
        for i, opt in enumerate(opts, 1):
            last_day = calendar.monthrange(year, opt)[1]
            row.append(InlineKeyboardButton(
                str(opt),
                callback_data=f"{parts}-{opt:02}-{last_day:02}"
            ))
            if i % 3 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                "📌 Pilih Bulan:", reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "📌 Pilih Bulan :", reply_markup=reply_markup
            )

    async def fault_button_handler(self, update, context, parts, page=1):
        per_page = 10
        page = int(page)
        _, crane_id, start_date, end_date = parts.split("|")
        print(parts)
        faults = self.maintenance_service.get_all_faults(crane_id, start_date, end_date)

        total_pages = math.ceil(len(faults) / per_page)
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        faults_page = faults[start_index:end_index]

        keyboard = [
            [InlineKeyboardButton(
                f"{f.fault_id}|{f.fault_name}",
                callback_data=f"{parts}|{f.fault_id}"
            )]
            for f in faults_page
        ]

        # Tombol navigasi halaman
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{parts}|page={page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{parts}|page={page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        await asyncio.sleep(0.5)
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "📌 Pilih Fault:", reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("📌 Pilih Fault:", reply_markup=reply_markup)
        except RetryAfter as e:
            wait = e.retry_after if hasattr(e, 'retry_after') else 5
            print(f"Flood control, retry after {wait}s")
            await asyncio.sleep(wait)
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "📌 Pilih Fault:", reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("📌 Pilih Fault:", reply_markup=reply_markup)
        except Exception as e:
            print(f"Error saat menampilkan fault list: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Gagal menampilkan daftar fault.")

    # ==============================
    #  FILE HANDLING
    # ==============================
    @admin_only
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print("Menerima dokumen...")
        document = update.message.document
        mime = document.mime_type
        
        # Generate unique file name with original extension
        ext = os.path.splitext(document.file_name)[1]
        file_path = f"temp/{uuid.uuid4()}{ext}"
        os.makedirs("temp", exist_ok=True)

        for attempt in range(3):
            try:
                print(f"Percobaan ke-{attempt + 1}: Mengambil file dari Telegram...")
                file = await context.bot.get_file(document.file_id)
                break
            except TimedOut:
                if attempt < 2:
                    await asyncio.sleep(5)
                else:
                    await update.message.reply_text("Gagal mengambil file dari Telegram setelah beberapa kali percobaan.")
                    return
            except Exception as e:
                print(f"Kesalahan saat mengambil file: {e}")
                await update.message.reply_text(f"Kesalahan saat mengambil file: {e}")
                return

        try:
            await file.download_to_drive(file_path)
            print(f"File berhasil diunduh ke {file_path}")

            # Gunakan thread untuk operasi blocking
            if mime == "application/zip":
                await asyncio.to_thread(self.zip_parser_service.parse_zip, file_path)
                await update.message.reply_text("Data dari file ZIP berhasil diproses dan disimpan ke database.")
            elif mime in ("application/x-rar-compressed", "application/vnd.rar"):
                await asyncio.to_thread(self.rar_parser_service.parse_rar, file_path)
                await update.message.reply_text("Data dari file RAR berhasil diproses dan disimpan ke database.")
            elif mime == "text/csv":
                await asyncio.to_thread(self.maintenance_service.add_fault, file_path)
                await update.message.reply_text("Data dari EventLib berhasil diproses dan disimpan ke database.")
            else:
                await update.message.reply_text("Mohon kirimkan file dalam format ZIP, RAR, atau CSV.")
        except Exception as e:
            logger.error("Error saat memproses file:", exc_info=True)
            await update.message.reply_text(f"Terjadi kesalahan saat memproses file: {e}")
        finally:
            # Bersihkan file sementara
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Gagal menghapus file sementara: {e}")

    # ==============================
    #  BOT EXECUTION
    # ==============================
    def run(self):
        print("Menjalankan polling...")
        self.application.run_polling()


if __name__ == "__main__":
    bot_instance = TelegramBot(BOT_TOKEN, maintenance_service)
    print("Bot sedang berjalan...")
    bot_instance.run()