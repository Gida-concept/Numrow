from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, User
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.future import select

from utils.logger import app_logger
from models.user import User as DBUser
from models.number import Number
import bot.keyboards as kb
import bot.messages as msg

# Create a router instance
main_router = Router()

# --- MOCK DATA (Global for search filtering) ---
ALL_COUNTRIES = [
    {'id': '0', 'name': '🇳🇬 Nigeria'},
    {'id': '1', 'name': '🇬🇭 Ghana'},
    {'id': '12', 'name': '🇺🇸 USA'},
    {'id': '2', 'name': '🇬🇧 UK'},
    {'id': '3', 'name': '🇨🇦 Canada'},
    {'id': '4', 'name': '🇧🇷 Brazil'},
    {'id': '5', 'name': '🇷🇺 Russia'},
    {'id': '6', 'name': '🇮🇳 India'},
    {'id': '7', 'name': '🇿🇦 South Africa'},
]

ALL_SERVICES = [
    {'id': 'wa', 'name': 'WhatsApp'},
    {'id': 'tg', 'name': 'Telegram'},
    {'id': 'fb', 'name': 'Facebook'},
    {'id': 'go', 'name': 'Google/Gmail'},
    {'id': 'ig', 'name': 'Instagram'},
    {'id': 'tw', 'name': 'Twitter/X'},
    {'id': 'nf', 'name': 'Netflix'},
    {'id': 'am', 'name': 'Amazon'},
    {'id': 'tik', 'name': 'TikTok'},
]

# Define the states for the order process
class OrderState(StatesGroup):
    choosing_country = State()
    searching_country = State() # NEW STATE
    choosing_service = State()
    searching_service = State() # NEW STATE
    choosing_number_type = State()
    confirming_price = State()

# --- User Upsert Logic ---
async def get_or_create_user(session, telegram_user: User) -> DBUser:
    """Retrieves a user from the DB or creates a new one."""
    query = select(DBUser).where(DBUser.telegram_id == telegram_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        user = DBUser(
            telegram_id=telegram_user.id,
            full_name=telegram_user.full_name,
            username=telegram_user.username,
            language_code=telegram_user.language_code
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        app_logger.info(f"New user created: {user}")
    return user

# --- Command Handlers ---

@main_router.message(CommandStart())
async def handle_start(message: Message, session):
    """Handler for the /start command."""
    user_data = await get_or_create_user(session, message.from_user)
    app_logger.info(f"User {user_data.telegram_id} started the bot.")
    
    await message.answer(
        msg.welcome_message(user_data.full_name),
        reply_markup=kb.main_menu_keyboard()
    )

# --- Main Menu Callbacks ---

@main_router.callback_query(F.data == "order_number")
async def cq_order_number(callback: CallbackQuery, state: FSMContext):
    """Starts the number ordering flow."""
    await callback.answer()
    
    # Show initial list of countries
    await callback.message.edit_text(
        msg.SELECT_COUNTRY,
        reply_markup=kb.country_selection_keyboard(ALL_COUNTRIES)
    )
    await state.set_state(OrderState.choosing_country)

@main_router.callback_query(F.data == "my_numbers")
async def cq_my_numbers(callback: CallbackQuery, session):
    """Shows active numbers."""
    await callback.answer()
    user_data = await get_or_create_user(session, callback.from_user)
    
    query = select(Number).where(
        Number.user_id == user_data.id,
        Number.status == "active"
    ).order_by(Number.created_at.desc())
    
    result = await session.execute(query)
    numbers = result.scalars().all()
    
    if not numbers:
        response_text = "📭 <b>You have no active numbers.</b>\n\nClick 'Order a Number' to get started."
    else:
        response_text = "📱 <b>Your Active Numbers:</b>\n\n"
        for num in numbers:
            response_text += (
                f"📞 <code>{num.phone_number}</code>\n"
                f"   Service: {num.service_code.upper()}\n"
                f"   Expires: {num.expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            )
    
    await callback.message.edit_text(response_text, reply_markup=kb.main_menu_keyboard())

@main_router.callback_query(F.data == "support")
async def cq_support(callback: CallbackQuery):
    """Shows support info."""
    await callback.answer()
    support_text = (
        "🆘 <b>Help & Support</b>\n\n"
        "📧 <b>Email:</b>\n• info@numrow.com\n• gidatechnologies@gmail.com"
    )
    await callback.message.edit_text(support_text, reply_markup=kb.main_menu_keyboard())

# --- COUNTRY SEARCH LOGIC ---

@main_router.callback_query(OrderState.choosing_country, F.data == "start_search_country")
async def cq_start_search_country(callback: CallbackQuery, state: FSMContext):
    """Asks user to type country name."""
    await callback.answer()
    await callback.message.edit_text(msg.SEARCH_COUNTRY_PROMPT)
    await state.set_state(OrderState.searching_country)

@main_router.message(OrderState.searching_country)
async def process_country_search(message: Message, state: FSMContext):
    """Filters countries based on user input."""
    search_query = message.text.lower().strip()
    
    # Filter the global list
    filtered_countries = [
        c for c in ALL_COUNTRIES 
        if search_query in c['name'].lower()
    ]
    
    if not filtered_countries:
        await message.answer(
            msg.NO_RESULTS,
            reply_markup=kb.country_selection_keyboard(ALL_COUNTRIES)
        )
    else:
        await message.answer(
            f"🔍 Found {len(filtered_countries)} results for '{message.text}':",
            reply_markup=kb.country_selection_keyboard(filtered_countries)
        )
    
    # Return to choosing state so clicking a button works
    await state.set_state(OrderState.choosing_country)

@main_router.callback_query(OrderState.choosing_country, F.data.startswith(kb.CB_PREFIX_COUNTRY))
async def cq_country_selected(callback: CallbackQuery, state: FSMContext):
    """Handles country selection."""
    country_id = callback.data.split(':')[1]
    await state.update_data(country_id=country_id)
    await callback.answer(f"Country selected.")
    
    # Show initial list of services
    await callback.message.edit_text(
        msg.SELECT_SERVICE,
        reply_markup=kb.service_selection_keyboard(ALL_SERVICES)
    )
    await state.set_state(OrderState.choosing_service)

# --- SERVICE SEARCH LOGIC ---

@main_router.callback_query(OrderState.choosing_service, F.data == "start_search_service")
async def cq_start_search_service(callback: CallbackQuery, state: FSMContext):
    """Asks user to type service name."""
    await callback.answer()
    await callback.message.edit_text(msg.SEARCH_SERVICE_PROMPT)
    await state.set_state(OrderState.searching_service)

@main_router.message(OrderState.searching_service)
async def process_service_search(message: Message, state: FSMContext):
    """Filters services based on user input."""
    search_query = message.text.lower().strip()
    
    filtered_services = [
        s for s in ALL_SERVICES 
        if search_query in s['name'].lower()
    ]
    
    if not filtered_services:
        await message.answer(
            msg.NO_RESULTS,
            reply_markup=kb.service_selection_keyboard(ALL_SERVICES)
        )
    else:
        await message.answer(
            f"🔍 Found {len(filtered_services)} results for '{message.text}':",
            reply_markup=kb.service_selection_keyboard(filtered_services)
        )
    
    await state.set_state(OrderState.choosing_service)

@main_router.callback_query(OrderState.choosing_service, F.data.startswith(kb.CB_PREFIX_SERVICE))
async def cq_service_selected(callback: CallbackQuery, state: FSMContext):
    """Handles service selection."""
    service_id = callback.data.split(':')[1]
    await state.update_data(service_id=service_id)
    await callback.answer(f"Service selected.")

    await callback.message.edit_text(
        msg.SELECT_NUMBER_TYPE,
        reply_markup=kb.number_type_keyboard()
    )
    await state.set_state(OrderState.choosing_number_type)

# --- Price & Payment Logic ---

@main_router.callback_query(OrderState.choosing_number_type, F.data.startswith(kb.CB_PREFIX_NUMBER_TYPE))
async def cq_type_selected(callback: CallbackQuery, state: FSMContext):
    """Handles number type selection."""
    number_type = callback.data.split(':')[1]
    await state.update_data(number_type=number_type)
    
    user_selections = await state.get_data()
    await callback.message.edit_text(msg.FETCHING_PRICE)

    from workers.pricing_worker import get_final_ngn_price
    
    final_price_ngn, price_ref = await get_final_ngn_price(
        user_selections['country_id'],
        user_selections['service_id'],
        user_selections['number_type']
    )
    
    if not final_price_ngn:
        await callback.message.edit_text(msg.SERVICE_UNAVAILABLE)
        return

    payment_id = f"temp_{callback.from_user.id}_{int(callback.message.date.timestamp())}"

    await callback.message.edit_text(
        msg.final_price_message(final_price_ngn),
        reply_markup=kb.payment_keyboard(payment_id, price_ref)
    )
    await state.set_state(OrderState.confirming_price)

@main_router.callback_query(F.data.startswith(kb.CB_PREFIX_PAY))
async def cq_pay_now(callback: CallbackQuery, state: FSMContext, session):
    """Handles Pay Now."""
    await callback.answer("Creating payment link...")
    
    parts = callback.data.split(':', 2)
    if len(parts) < 3: return
    price_ref = parts[2]
    
    user_data = await get_or_create_user(session, callback.from_user)
    selections = await state.get_data()
    
    from workers.pricing_worker import get_final_ngn_price
    final_price_ngn, _ = await get_final_ngn_price(
        selections.get('country_id'), selections.get('service_id'), selections.get('number_type')
    )
    
    if not final_price_ngn:
        await callback.message.answer(msg.SERVICE_UNAVAILABLE)
        return
    
    from workers.payment_worker import create_payment_link
    payment_url = await create_payment_link(session, user_data.id, final_price_ngn, price_ref)
    
    if payment_url:
        await callback.message.edit_text(
            msg.payment_link_message(payment_url),
            reply_markup=kb.payment_link_keyboard(payment_url)
        )
    else:
        await callback.message.answer(msg.GENERIC_ERROR)

# --- Cancel ---
@main_router.callback_query(F.data.startswith(kb.CB_PREFIX_CANCEL))
async def cq_cancel_flow(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Cancelled.")
    await state.clear()
    await callback.message.edit_text(
        msg.welcome_message(callback.from_user.full_name),
        reply_markup=kb.main_menu_keyboard()
    )
