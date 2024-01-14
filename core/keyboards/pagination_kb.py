from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_pagination_kb(data):
    builder = InlineKeyboardBuilder()
    for button_data in data:
        builder.button(
            text=button_data['text'],
            callback_data=PaginationCallbackFactory(action=button_data['action'], page=button_data['page'])
        )
    return builder.as_markup()


class PaginationCallbackFactory(CallbackData, prefix='pagination'):
    action: str
    page: int
