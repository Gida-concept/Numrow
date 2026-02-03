from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Callback Data Prefixes ---
CB_PREFIX_COUNTRY = "country:"
CB_PREFIX_SERVICE = "service:"
CB_PREFIX_NUMBER_TYPE = "numtype:"
CB_PREFIX_PAY = "pay:"
CB_PREFIX_CANCEL = "cancel:"
CB_BACK = "back:"

# --- Main Menu & General Keyboards ---
def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Creates the main menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🛒 Order a Number", callback_data="order_number"))
    builder.row(
        InlineKeyboardButton(text="My Numbers", callback_data="my_numbers"),
        InlineKeyboardButton(text="Help & Support", callback_data="support")
    )
    return builder.as_markup()

def initial_selection_keyboard(list_callback: str, search_callback: str, back_callback: str) -> InlineKeyboardMarkup:
    """Initial keyboard with 'See All' and 'Search' options."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 See All", callback_data=list_callback),
        InlineKeyboardButton(text="🔍 Search", callback_data=search_callback)
    )
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data=back_callback))
    return builder.as_markup()

def load_more_list_keyboard(items: list, prefix: str, offset: int, total_count: int, back_callback: str) -> InlineKeyboardMarkup:
    """
    Creates a keyboard for a list with a 'Load More' button if there are more items.
    """
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.add(InlineKeyboardButton(text=item['name'], callback_data=f"{prefix}{item['id']}"))
    builder.adjust(2)

    # If there are more items to load, show a 'Load More' button
    if offset + len(items) < total_count:
        next_offset = offset + len(items)
        builder.row(InlineKeyboardButton(
            text="➕ Load More", 
            callback_data=f"load_more:{prefix.rstrip(':')}:{next_offset}"
        ))
        
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data=back_callback))
    return builder.as_markup()

def number_type_keyboard() -> InlineKeyboardMarkup:
    """Creates keyboard for selecting number type with a Back button."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏳ Temporary", callback_data=f"{CB_PREFIX_NUMBER_TYPE}temp"))
    builder.row(InlineKeyboardButton(text="🗓️ Rent", callback_data=f"{CB_PREFIX_NUMBER_TYPE}rent"))
    builder.row(InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data=f"{CB_BACK}main_menu"))
    return builder.as_markup()

def payment_keyboard(price_ref: str) -> InlineKeyboardMarkup:
    """Creates the 'Pay Now' keyboard with a Back button."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Pay Now", callback_data=f"{CB_PREFIX_PAY}{price_ref}"))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data=f"{CB_BACK}service_select"))
    return builder.as_markup()

def payment_link_keyboard(url: str) -> InlineKeyboardMarkup:
    """Creates a keyboard with a button to open the payment URL."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔗 Open Payment Page", url=url))
    return builder.as_markup()
