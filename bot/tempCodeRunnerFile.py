    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        document = update.message.document
        if document.mime_type != "application/rar":
            await update.message.reply_text("Mohon kirimkan file dalam format RAR.")
            return

        file_path = f"temp/{document.file_name}"
        os.makedirs("temp", exist_ok=True)
        file = await context.bot.get_file(document.file_id)
        await file.download_to_drive(file_path)

        try:
            rar_parser_service.parse_rar(file_path)
            await update.message.reply_text("Data berhasil diproses dan disimpan ke database.")
        except Exception as e:
            await update.message.reply_text(f"Terjadi kesalahan: {e}")
        os.remove(file_path)