# bot/admin_auth.py
import os
from telegram import Update
from telegram.ext import ContextTypes
import telegram
import functools

def get_admin_ids():
    """Ambil daftar admin dari environment variable"""
    admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
    return {int(id_str.strip()) for id_str in admin_ids_str.split(',') if id_str.strip().isdigit()}

def is_admin(user_id: int) -> bool:
    """Cek apakah user adalah admin"""
    print(f"Memeriksa apakah user_id {user_id} adalah admin...")
    return user_id in get_admin_ids()

def admin_only(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Jika fungsi adalah method, maka urutannya: self, update, context
        if len(args) >= 3:
            self_obj = args[0]
            update = args[1]
            context = args[2]
        else:
            update = args[0]
            context = args[1]

        user_id = update.effective_user.id

        if not is_admin(user_id):
            if update.message:
                await update.message.reply_text(
                    "⛔ *PERINGATAN: Akses Ditolak!*\n\n"
                    f"User ID Anda: `{user_id}`",
                    parse_mode=telegram.constants.ParseMode.MARKDOWN
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⛔ *PERINGATAN: Akses Ditolak!*",
                    parse_mode=telegram.constants.ParseMode.MARKDOWN
                )
            return
        return await func(*args, **kwargs)
    return wrapper




