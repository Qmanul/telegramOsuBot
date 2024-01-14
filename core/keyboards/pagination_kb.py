from typing import Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_pagination_kb(page):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="<<", callback_data=PaginationCallbackFactory(action="backward", page=page)
    )
    builder.button(
        text=">>", callback_data=PaginationCallbackFactory(action="forward", page=page)
    )
    return builder.as_markup()


class PaginationCallbackFactory(CallbackData, prefix='pagination'):
    action: str
    page: int
