from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Callback Data Prefixes ---
CB_PREFIX_COUNTRY = "country:"
CB_PREFIX_SERVICE = "service:"
CB_PREFIX_NUMBER_TYPE = "numtype:"
CB_PREFIX_RENT_DURATION = "rentdays:"  # <-- This was missing
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

# --- Helper Function for Bottom Buttons ---
def _add_bottom_buttons(builder: InlineKeyboardBuilder, search_callback: str):
    """Helper to add search and cancel buttons."""
    builder.row(
        InlineKeyboardButton(text="🔍 Search", callback_data=search_callback),
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"{CB_PREFIX_CANCEL}main")
    )

# --- Dynamic Keyboards for Service Selection ---

def country_selection_keyboard(countries: list[dict]) -> InlineKeyboardMarkup:
    """Creates a keyboard for selecting a country."""
    builder = InlineKeyboardBuilder()
    
    for country in countries:
        builder.add(
            InlineKeyboardButton(
                text=country['name'],
                callback_data=f"{CB_PREFIX_COUNTRY}{country['id']}"
            )
        )
    
    builder.adjust(2) # 2 columns
    _add_bottom_buttons(builder, "start_search_country")
    return builder.as_markup()

def service_selection_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    """Creates a keyboard for selecting a service."""
    builder = InlineKeyboardBuilder()
    
    for service in services:
        builder.add(
            InlineKeyboardButton(
                text=service['name'],
                callback_data=f"{CB_PREFIX_SERVICE}{service['id']}"
            )
        )
    
    builder.adjust(2)
    _add_bottom_buttons(builder, "start_search_service")
    return builder.as_markup()

def number_type_keyboard() -> InlineKeyboardMarkup:
    """Creates a keyboard for selecting number type (temp vs rent)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⏳ Temporary", 
            callback_data=f"{CB_PREFIX_NUMBER_TYPE}temporary"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗓️ Rent (3-30 Days)",
            callback_data=f"{CB_PREFIX_NUMBER_TYPE}rent"
        )
    )
    return builder.as_markup()

def rent_duration_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting rental duration in days."""
    builder = InlineKeyboardBuilder()
    durations = [3, 7, 14, 30]
    
    for days in durations:
        builder.add(
            InlineKeyboardButton(
                text=f"{days} Days", 
                callback_data=f"{CB_PREFIX_RENT_DURATION}{days}"
            )
        )
    
    builder.adjust(2) # 2 columns
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_type")
    )
    return builder.as_markup()

# --- Payment Keyboard ---

def payment_keyboard(payment_id: str, price_ref: str) -> InlineKeyboardMarkup:
    """Creates the 'Pay Now' keyboard."""
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
            callback_data=f"{CB_PREFIX_CANCEL}main"
        )
    )
    return builder.as_markup()

def payment_link_keyboard(url: str) -> InlineKeyboardMarkup:
    """Creates a keyboard with a button to open the payment URL."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔗 Open Payment Page", url=url))
    return builder.as_markup()
