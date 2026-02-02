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
