"""
Centralized repository for all user-facing messages.
"""

# --- Welcome & Main Menu ---
def welcome_message(name: str) -> str:
    """Greets the user upon starting the bot."""
    return (
        f"👋 Hello, <b>{name}</b>!\n\n"
        "Welcome to the Automated Number Service.\n\n"
        "Please select an option below to get started."
    )

MAIN_MENU_TEXT = "Please choose a service from the menu:"

# --- Service Selection Flow ---
SELECT_COUNTRY = "Please select the country for the service:"
SELECT_SERVICE = "Please select the service you need a number for:"
SELECT_NUMBER_TYPE = "Please choose the number type:"

def service_selection_summary(country: str, service: str, number_type: str) -> str:
    """Shows the user their current selection."""
    return (
        f"🔍 Your Selection:\n"
        f"  - Country: <b>{country}</b>\n"
        f"  - Service: <b>{service}</b>\n"
        f"  - Type: <b>{number_type}</b>\n\n"
        "Please wait while we calculate the price..."
    )

# --- Pricing and Payment ---
FETCHING_PRICE = "⚙️ Fetching the best price for you, please wait..."

def final_price_message(price_ngn: float) -> str:
    """
    Displays the final, non-negotiable price in NGN to the user.
    """
    formatted_price = f"{price_ngn:,.2f}"
    return (
        f"💰 <b>Final Price: ₦{formatted_price}</b>\n\n"
        "This is the total amount you will pay. Click 'Pay Now' to proceed."
    )

def payment_link_message(url: str) -> str:
    """Provides the Paystack payment link."""
    return (
        "✅ Your payment link is ready!\n\n"
        f"Please complete your payment here: {url}\n\n"
        "I will notify you once the payment is confirmed."
    )

PAYMENT_SUCCESSFUL = (
    "🎉 <b>Payment Successful!</b>\n\n"
    "We are now ordering your number. Please wait a moment..."
)

PAYMENT_FAILED = "❌ <b>Payment Failed or Canceled.</b>\n\nPlease try again or select a different option."

# --- Number & SMS Handling ---
def number_issued_message(number: str, expiry_time: str) -> str:
    """Informs the user that their number has been issued."""
    return (
        f"✅ Your number is ready!\n\n"
        f"📞 <b>Number:</b> <code>{number}</code>\n"
        f"⏳ <b>Expires:</b> in {expiry_time}\n\n"
        "I will automatically listen for incoming SMS and forward them to you here."
    )

def new_sms_message(sms_code: str, full_text: str) -> str:
    """Forwards a new SMS to the user."""
    return (
        f"📩 <b>New SMS Received!</b>\n\n"
        f"<b>Code:</b> <code>{sms_code}</code>\n\n"
        f"<b>Full Text:</b>\n<pre>{full_text}</pre>"
    )

NUMBER_EXPIRED = "⌛️ Your temporary number has expired. Please purchase a new one if needed."
NO_SMS_YET = "No SMS received yet. Still listening..."

# --- Error and System Messages ---
GENERIC_ERROR = "⚠️ An unexpected error occurred. Please try again later or contact support."
PRICE_EXPIRED = "⚠️ The price for this service has expired. Please start over to get a new price."
SERVICE_UNAVAILABLE = "Sorry, this service is currently unavailable. Please try again later."
INVALID_SELECTION = "Invalid selection. Please use the buttons provided."

# --- Search Prompts ---
SEARCH_COUNTRY_PROMPT = "🔍 <b>Search Country</b>\n\nPlease type the name of the country you are looking for:"
SEARCH_SERVICE_PROMPT = "🔍 <b>Search Service</b>\n\nPlease type the name of the service you are looking for:"
NO_RESULTS = "❌ No matching results found. Showing all options again:"
