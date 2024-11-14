class AdminHandler:
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать админ-панель"""
        keyboard = [
            ['👥 Сотрудники', '🏪 Магазины'],
            ['👨‍💼 Администраторы'],
            ['↩️ Назад']
        ]
        await update.message.reply_text(
            "Панель администратора:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return ADMIN_MENU

    async def show_user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню управления сотрудником"""
        keyboard = [
            ['👔 Изменить должность'],
            ['🏪 Изменить магазин'],
            ['❌ Удалить админ права'],
            ['↩️ Назад']
        ]
        
        # Проверяем, есть ли у выбранного пользователя права админа
        user_id = context.user_data.get('selected_user_id')
        user_data = self.db.get_user_data(user_id)
        
        if not user_data:
            await update.message.reply_text("Ошибка: пользователь не найден")
            return await self.show_admin_panel(update, context)
        
        _, _, _, position, is_admin, _, _ = user_data
        
        # Если у пользователя нет прав админа, убираем кнопку удаления прав
        if not is_admin:
            keyboard.pop(2)  # Удаляем кнопку "Удалить админ права"
        
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return USER_MANAGEMENT

    async def remove_admin_rights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление прав администратора"""
        if update.message.text == '↩️ Назад':
            return await self.show_user_management(update, context)
        
        user_id = context.user_data.get('selected_user_id')
        user_data = self.db.get_user_data(user_id)
        
        if not user_data:
            await update.message.reply_text("Ошибка: пользователь не найден")
            return await self.show_admin_panel(update, context)
        
        # Убираем права админа
        self.db.set_admin_status(user_id, False)
        await update.message.reply_text("Права администратора успешно удалены")
        return await self.show_user_management(update, context)