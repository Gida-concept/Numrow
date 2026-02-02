from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Callback Data Prefixes ---
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

def country_selection_keyboard(countries: list[dict], enable_search: bool = True) -> InlineKeyboardMarkup:
    """
    Creates a keyboard for selecting a country.
    """
    builder = InlineKeyboardBuilder()
    
    # Add country buttons
    for country in countries:
        builder.add(
            InlineKeyboardButton(
                text=country['name'],
                callback_data=f"{CB_PREFIX_COUNTRY}{country['id']}"
            )
        )
    
    builder.adjust(2) # Grid of 2 columns
    
    # Add Search and Cancel buttons at the bottom
    bottom_buttons = []
    if enable_search:
        bottom_buttons.append(InlineKeyboardButton(text="🔍 Search Country", callback_data="start_search_country"))
    
    bottom_buttons.append(InlineKeyboardButton(text="❌ Cancel", callback_data=f"{CB_PREFIX_CANCEL}main"))
    
    builder.row(*bottom_buttons)
    
    return builder.as_markup()

def service_selection_keyboard(services: list[dict], enable_search: bool = True) -> InlineKeyboardMarkup:
    """
    Creates a keyboard for selecting a service.
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
    
    bottom_buttons = []
    if enable_search:
        bottom_buttons.append(InlineKeyboardButton(text="🔍 Search Service", callback_data="start_search_service"))
    
    bottom_buttons.append(InlineKeyboardButton(text="❌ Cancel", callback_data=f"{CB_PREFIX_CANCEL}main"))
    
    builder.row(*bottom_buttons)
    
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
