from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.services.shop import get_all_products, get_products_by_category, get_product_by_id, get_all_links, get_driver_info

# Хранилище кастомных браслетов пользователей
user_bracelets = {}

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Главное меню
    if data == "back_to_menu":
        await show_main_menu(query)
    
    # Каталог браслетов
    elif data == "catalog_bracelets" or data == "all_bracelets":
        await show_catalog(query)
    
    # Покупка готового браслета
    elif data.startswith("buy_"):
        product_id = data.replace("buy_", "")
        await confirm_purchase(query, product_id)
    
    # Сборка кастомного браслета
    elif data == "custom_bracelet_start":
        user_bracelets[user_id] = []
        await show_links_for_custom(query, user_id)
    
    # Добавление звена к браслету
    elif data.startswith("add_link_"):
        link_id = data.replace("add_link_", "")
        await add_link_to_bracelet(query, user_id, link_id)
    
    # Завершение сборки
    elif data == "finish_custom":
        await finish_custom_bracelet(query, user_id)
    
    # Удаление звена
    elif data.startswith("remove_link_"):
        link_id = data.replace("remove_link_", "")
        if user_id in user_bracelets:
            user_bracelets[user_id] = [l for l in user_bracelets[user_id] if l.link_id != link_id]
        await show_links_for_custom(query, user_id)
    
    # О магазине
    elif data == "about":
        await show_about(query)

async def show_main_menu(query):
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🏁 Каталог браслетов", callback_data="catalog_bracelets")],
        [InlineKeyboardButton("🛠️ Собрать свой браслет", callback_data="custom_bracelet_start")],
        [InlineKeyboardButton("ℹ️ О магазине", callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏁 *NOMINATION F1 BRACELETS* 🏁\n\n"
        "Что ты выбираешь?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def show_catalog(query):
    """Показать каталог готовых браслетов"""
    products = get_all_products()
    
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"💰 {product.name} - {product.price}₽",
                callback_data=f"buy_{product.product_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏁 *Каталог готовых браслетов*\n\n"
        "Выбери браслет понравившегося пилота:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def confirm_purchase(query, product_id):
    """Подтвердить покупку"""
    product = get_product_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ Товар не найден.")
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ Оформить заказ", callback_data=f"order_{product_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="catalog_bracelets")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🏁 *{product.name}*\n\n"
        f"💰 Цена: {product.price}₽\n"
        f"📝 {product.description}\n\n"
        f"Хочешь заказать?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def show_links_for_custom(query, user_id):
    """Показать звенья для сборки браслета"""
    links = get_all_links()
    current_links = user_bracelets.get(user_id, [])
    
    keyboard = []
    for link in links:
        driver_info = get_driver_info(link.driver)
        button_text = f"#{driver_info['number']} {link.name}"
        
        # Показать, если уже добавлено
        if any(l.link_id == link.link_id for l in current_links):
            button_text = f"✅ {button_text}"
            callback = f"remove_link_{link.link_id}"
        else:
            callback = f"add_link_{link.link_id}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("🛠️ Готово! Оформить", callback_data="finish_custom")])
    keyboard.append([InlineKeyboardButton("⬅️ Отмена", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    selected_count = len(current_links)
    total_price = sum(l.price for l in current_links)
    
    text = f"""🛠️ *Собери свой браслет Nomination*

Выбрано звеньев: {selected_count}
💰 Сумма: {total_price}₽

Выбери пилотов (клик = добавить/удалить):"""
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def add_link_to_bracelet(query, user_id, link_id):
    """Добавить звено к браслету"""
    from src.services.shop import get_link_by_id
    
    if user_id not in user_bracelets:
        user_bracelets[user_id] = []
    
    link = get_link_by_id(link_id)
    if link and not any(l.link_id == link_id for l in user_bracelets[user_id]):
        user_bracelets[user_id].append(link)
    
    await show_links_for_custom(query, user_id)

async def finish_custom_bracelet(query, user_id):
    """Завершить сборку браслета"""
    links = user_bracelets.get(user_id, [])
    
    if not links:
        await query.answer("❌ Выбери хотя бы одно звено!", show_alert=True)
        return
    
    total_price = sum(l.price for l in links)
    
    links_text = "\n".join([f"#{get_driver_info(l.driver)['number']} {l.name}" for l in links])
    
    keyboard = [
        [InlineKeyboardButton("✅ Оформить заказ", callback_data=f"order_custom_{user_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="custom_bracelet_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""🏁 *Твой кастомный браслет готов!*

📋 Состав:
{links_text}

💰 Итого: {total_price}₽

Хочешь оформить заказ?"""
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def show_about(query):
    """О магазине"""
    keyboard = [
        [InlineKeyboardButton("🌐 Instagram", url="https://instagram.com/alinv1xf")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "ℹ️ *О нас*\n\n"
        "🏁 NOMINATION F1 BRACELETS\n\n"
        "Официальный магазин браслетов Nomination с символикой Формулы-1.\n\n"
        "✨ Качественные браслеты всех пилотов!\n"
        "🛠️ Возможность собрать свой уникальный браслет\n"
        "⚡ Быстрая доставка\n\n"
        "🌐 @alinv1xf",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )