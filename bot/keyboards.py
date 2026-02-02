from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

CB_PREFIX_COUNTRY = "country:"
CB_PREFIX_SERVICE = "service:"
CB_PREFIX_NUMBER_TYPE = "numtype:"
CB_PREFIX_PAY = "pay:"
CB_PREFIX_CANCEL = "cancel:"
CB_BACK = "back:"

def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🛒 Order a Number", callback_data="order_number"))
    builder.row(
        InlineKeyboardButton(text="My Numbers", callback_data="my_numbers"),
        InlineKeyboardButton(text="Help & Support", callback_data="support")
    )
    return builder.as_markup()

def country_selection_keyboard(countries: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in countries:
        builder.add(InlineKeyboardButton(text=country['name'], callback_data=f"{CB_PREFIX_COUNTRY}{country['id']}"))
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="🔍 Search", callback_data="start_search_country"),
        InlineKeyboardButton(text="⬅️ Main Menu", callback_data=f"{CB_BACK}main_menu")
    )
    return builder.as_markup()

def service_selection_keyboard(services: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.add(InlineKeyboardButton(text=service['name'], callback_data=f"{CB_PREFIX_SERVICE}{service['id']}"))
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="🔍 Search", callback_data="start_search_service"),
        InlineKeyboardButton(text="⬅️ Back", callback_data=f"{CB_BACK}country_select")
    )
    return builder.as_markup()

def number_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏳ Temporary", callback_data=f"{CB_PREFIX_NUMBER_TYPE}temp"))
    builder.row(InlineKeyboardButton(text="🗓️ Rent", callback_data=f"{CB_PREFIX_NUMBER_TYPE}rent"))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data=f"{CB_BACK}service_select"))
    return builder.as_markup()

def payment_keyboard(price_ref: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Pay Now", callback_data=f"{CB_PREFIX_PAY}{price_ref}"))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data=f"{CB_BACK}type_select"))
    return builder.as_markup()

def payment_link_keyboard(url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔗 Open Payment Page", url=url))
    return builder.as_markup()
