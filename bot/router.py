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
from workers import pricing_worker, payment_worker
from config.constants import PVA_PINS_COUNTRIES, PVA_PINS_SERVICES

main_router = Router()

class OrderState(StatesGroup):
    choosing_country = State()
    searching_country = State()
    choosing_service = State()
    searching_service = State()
    choosing_number_type = State()
    choosing_rent_duration = State()
    confirming_price = State()

async def get_or_create_user(session, telegram_user: User) -> DBUser:
    """Gets or creates a user in the database."""
    query = select(DBUser).where(DBUser.telegram_id == telegram_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        user = DBUser(
            telegram_id=telegram_user.id, full_name=telegram_user.full_name,
            username=telegram_user.username, language_code=telegram_user.language_code
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

@main_router.message(CommandStart())
async def handle_start(message: Message, session):
    """Handler for the /start command."""
    user_data = await get_or_create_user(session, message.from_user)
    await message.answer(msg.welcome_message(user_data.full_name), reply_markup=kb.main_menu_keyboard())

# --- MAIN MENU ---
@main_router.callback_query(F.data == "order_number")
async def cq_order_number(callback: CallbackQuery, state: FSMContext):
    """Starts the number ordering flow by showing countries."""
    await callback.answer()
    await callback.message.edit_text(msg.SELECT_COUNTRY, reply_markup=kb.country_selection_keyboard(PVA_PINS_COUNTRIES))
    await state.set_state(OrderState.choosing_country)

@main_router.callback_query(F.data == "my_numbers")
async def cq_my_numbers(callback: CallbackQuery, session):
    """Shows the user's active numbers."""
    await callback.answer()
    
    user_data = await get_or_create_user(session, callback.from_user)
    
    query = select(Number).where(
        Number.user_id == user_data.id,
        Number.status == "active"
    ).order_by(Number.created_at.desc())
    
    result = await session.execute(query)
    numbers = result.scalars().all()
    
    if not numbers:
        response_text = (
            "📭 <b>You have no active numbers.</b>\n\n"
            "Click 'Order a Number' to get started."
        )
    else:
        response_text = "📱 <b>Your Active Numbers:</b>\n\n"
        for num in numbers:
            response_text += (
                f"📞 <code>{num.phone_number}</code>\n"
                f"   Service: {num.service_code.upper()}\n"
                f"   Expires: {num.expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            )
    
    await callback.message.edit_text(
        response_text,
        reply_markup=kb.main_menu_keyboard()
    )

@main_router.callback_query(F.data == "support")
async def cq_support(callback: CallbackQuery):
    """Shows support contact information."""
    await callback.answer()
    
    support_text = (
        "🆘 <b>Help & Support</b>\n\n"
        "If you need assistance or have any questions, please contact us:\n\n"
        "📧 <b>Email:</b>\n"
        "• info@numrow.com\n"
        "• gidatechnologies@gmail.com\n\n"
        "We typically respond within 24 hours."
    )
    
    await callback.message.edit_text(
        support_text,
        reply_markup=kb.main_menu_keyboard()
    )

# --- COUNTRY FLOW ---
@main_router.callback_query(OrderState.choosing_country, F.data == "start_search_country")
async def cq_start_search_country(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(msg.SEARCH_COUNTRY_PROMPT)
    await state.set_state(OrderState.searching_country)

@main_router.message(OrderState.searching_country)
async def process_country_search(message: Message, state: FSMContext):
    search_query = message.text.lower().strip()
    filtered = [c for c in PVA_PINS_COUNTRIES if search_query in c['name'].lower()]
    reply_markup = kb.country_selection_keyboard(filtered if filtered else PVA_PINS_COUNTRIES)
    reply_text = f"Found {len(filtered)} results:" if filtered else msg.NO_RESULTS
    await message.answer(reply_text, reply_markup=reply_markup)
    await state.set_state(OrderState.choosing_country)

@main_router.callback_query(OrderState.choosing_country, F.data.startswith(kb.CB_PREFIX_COUNTRY))
async def cq_country_selected(callback: CallbackQuery, state: FSMContext):
    country_id = callback.data.split(':')[1]
    await state.update_data(country_id=country_id)
    await callback.answer("Country selected.")
    await callback.message.edit_text(msg.SELECT_SERVICE, reply_markup=kb.service_selection_keyboard(PVA_PINS_SERVICES))
    await state.set_state(OrderState.choosing_service)

# --- SERVICE FLOW ---
@main_router.callback_query(OrderState.choosing_service, F.data == "start_search_service")
async def cq_start_search_service(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(msg.SEARCH_SERVICE_PROMPT)
    await state.set_state(OrderState.searching_service)

@main_router.message(OrderState.searching_service)
async def process_service_search(message: Message, state: FSMContext):
    search_query = message.text.lower().strip()
    filtered = [s for s in PVA_PINS_SERVICES if search_query in s['name'].lower()]
    reply_markup = kb.service_selection_keyboard(filtered if filtered else PVA_PINS_SERVICES)
    reply_text = f"Found {len(filtered)} results:" if filtered else msg.NO_RESULTS
    await message.answer(reply_text, reply_markup=reply_markup)
    await state.set_state(OrderState.choosing_service)

@main_router.callback_query(OrderState.choosing_service, F.data.startswith(kb.CB_PREFIX_SERVICE))
async def cq_service_selected(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split(':')[1]
    await state.update_data(service_id=service_id)
    await callback.answer("Service selected.")
    await callback.message.edit_text(msg.SELECT_NUMBER_TYPE, reply_markup=kb.number_type_keyboard())
    await state.set_state(OrderState.choosing_number_type)

# --- NUMBER TYPE & DURATION FLOW ---
@main_router.callback_query(OrderState.choosing_number_type, F.data.startswith(kb.CB_PREFIX_NUMBER_TYPE))
async def cq_type_selected(callback: CallbackQuery, state: FSMContext):
    number_type = callback.data.split(':')[1]
    await state.update_data(number_type=number_type)

    if number_type == 'temporary':
        await process_price_request(callback, state)
    elif number_type == 'rent':
        await callback.message.edit_text("🗓️ Please select the rental duration:", reply_markup=kb.rent_duration_keyboard())
        await state.set_state(OrderState.choosing_rent_duration)

@main_router.callback_query(OrderState.choosing_rent_duration, F.data == "back_to_type")
async def cq_back_to_type(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(msg.SELECT_NUMBER_TYPE, reply_markup=kb.number_type_keyboard())
    await state.set_state(OrderState.choosing_number_type)

@main_router.callback_query(OrderState.choosing_rent_duration, F.data.startswith(kb.CB_PREFIX_RENT_DURATION))
async def cq_rent_duration_selected(callback: CallbackQuery, state: FSMContext):
    rent_days = int(callback.data.split(':')[1])
    await state.update_data(rent_days=rent_days)
    await process_price_request(callback, state)

# --- PRICING & PAYMENT ---
async def process_price_request(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(msg.FETCHING_PRICE)
    user_selections = await state.get_data()
    
    price, price_ref, duration = await pricing_worker.get_final_price(
        country_id=user_selections['country_id'],
        service_id=user_selections['service_id'],
        number_type=user_selections['number_type'],
        rent_days=user_selections.get('rent_days')
    )
    
    if not price:
        await callback.message.edit_text(msg.SERVICE_UNAVAILABLE)
        return

    payment_id = f"temp_{callback.from_user.id}_{int(callback.message.date.timestamp())}"
    await callback.message.edit_text(
        msg.final_price_message(price, duration),
        reply_markup=kb.payment_keyboard(payment_id, price_ref)
    )
    await state.set_state(OrderState.confirming_price)

@main_router.callback_query(F.data.startswith(kb.CB_PREFIX_PAY))
async def cq_pay_now(callback: CallbackQuery, state: FSMContext, session):
    await callback.answer("Creating payment link...")
    parts = callback.data.split(':', 2)
    if len(parts) < 3: return
    price_ref = parts[2]
    
    user_data = await get_or_create_user(session, callback.from_user)
    selections = await state.get_data()
    
    price, _, __ = await pricing_worker.get_final_price(
        country_id=selections.get('country_id'), service_id=selections.get('service_id'),
        number_type=selections.get('number_type'), rent_days=selections.get('rent_days')
    )
    if not price: return await callback.message.answer(msg.SERVICE_UNAVAILABLE)
    
    payment_url = await payment_worker.create_payment_link(session, user_data.id, price, price_ref)
    
    if payment_url:
        await callback.message.edit_text(
            msg.payment_link_message(payment_url), reply_markup=kb.payment_link_keyboard(payment_url)
        )
    else:
        await callback.message.answer(msg.GENERIC_ERROR)

# --- CANCEL ---
@main_router.callback_query(F.data.startswith(kb.CB_PREFIX_CANCEL))
async def cq_cancel_flow(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Cancelled.")
    await state.clear()
    await callback.message.edit_text(msg.welcome_message(callback.from_user.full_name), reply_markup=kb.main_menu_keyboard())
