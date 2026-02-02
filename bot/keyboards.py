from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Callback Data Prefixes ---
# Using prefixes in callback data is a best practice. It helps in routing
# callbacks to the correct handlers. For example, any callback starting with
# "country:" will be handled by the country selection logic.
CB_PREFIX_COUNTRY = "country:"
CB_PREFIX_SERVICE = "service:"
CB_PREFIX_NUMBER_TYPE = "numtype:"
CB_PREFIX_PAY = "pay:"
CB_PREFIX_CANCEL = "cancel:"

# --- Main Menu & General Keyboards ---
def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Creates the main menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Order a Number", callback_data="order_number")
    )
    builder.row(
        InlineKeyboardButton(text="My Numbers", callback_data="my_numbers"),
        InlineKeyboardButton(text="Help & Support", callback_data="support")
    )
    return builder.as_markup()

# --- Dynamic Keyboards for Service Selection ---

def country_selection_keyboard(countries: list[dict]) -> InlineKeyboardMarkup:
    """
    Creates a keyboard for selecting a country.
    'countries' is expected to be a list of dicts, e.g., [{'id': '0', 'name': 'Nigeria'}]
    """
    builder = InlineKeyboardBuilder()
    for country in countries:
        builder.add(
            InlineKeyboardButton(
                text=country['name'],
                callback_data=f"{CB_PREFIX_COUNTRY}{country['id']}"
            )
        )
    # Adjust the width of the grid. 2 buttons per row.
    builder.adjust(2)
    return builder.as_markup()

def service_selection_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    """
    Creates a keyboard for selecting a service.
    'services' is expected to be a list of dicts, e.g., [{'id': 'wa', 'name': 'WhatsApp'}]
    """
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.add(
            InlineKeyboardButton(
                text=service['name'],
                callback_data=f"{CB_PREFIX_SERVICE}{service['id']}"
            )
        )
    builder.adjust(2)
    return builder.as_markup()

def number_type_keyboard() -> InlineKeyboardMarkup:
    """Creates a keyboard for selecting number type (temp vs rent)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⏳ Temporary (20 mins)",
            callback_data=f"{CB_PREFIX_NUMBER_TYPE}temporary"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗓️ Rent (3+ days)",
            callback_data=f"{CB_PREFIX_NUMBER_TYPE}rent"
        )
    )
    return builder.as_markup()

# --- Payment Keyboard ---

def payment_keyboard(payment_id: str, price_ref: str) -> InlineKeyboardMarkup:
    """
    Creates the 'Pay Now' keyboard.
    'payment_id' or a unique reference is needed to lock the price.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💳 Pay Now",
            callback_data=f"{CB_PREFIX_PAY}{payment_id}:{price_ref}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data=f"{CB_PREFIX_CANCEL}main_menu"
        )
    )
    return builder.as_markup()

def payment_link_keyboard(url: str) -> InlineKeyboardMarkup:
    """Creates a keyboard with a button to open the payment URL."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔗 Open Payment Page", url=url))
    return builder.as_markup()