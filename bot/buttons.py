from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def paginate_buttons():
    kb_list = [
        [InlineKeyboardButton(text="Предыдущая", callback_data='1')],
        [InlineKeyboardButton(text="Следующая", callback_data='2')]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_list)
    return keyboard
