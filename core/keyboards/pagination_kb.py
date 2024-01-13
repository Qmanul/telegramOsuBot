from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

builder = InlineKeyboardBuilder()
builder.add(InlineKeyboardButton(
    text="<", callback_data="pagination_backward")
)
builder.add(InlineKeyboardButton(
    text=">", callback_data="pagination_forward")
)