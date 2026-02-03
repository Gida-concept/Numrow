import math
import aiogram.exceptions
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, User
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from utils.logger import app_logger
from models.user import User as DBUser
from models.number import Number
import bot.keyboards as kb
import bot.messages as msg
from services.pva_service import pva_service
from workers import pricing_worker, payment_worker

main_router = Router()
ITEMS_PER_PAGE = 10
LOAD_MORE_COUNT = 10

class OrderState(StatesGroup):
    choosing_type = State()
    choosing_country = State()
    searching_country = State()
    choosing_service = State()
    searching_service = State()
    confirming_price = State()

async def get_or_create_user(session, telegram_user: User) -> DBUser:
    query = select(DBUser).where(DBUser.telegram_id == telegram_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        user = DBUser(telegram_id=telegram_user.id, full_name=telegram_user.full_name, username=telegram_user.username, language_code=telegram_user.language_code)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

@main_router.message(CommandStart())
async def handle_start(message: Message, session):
    user_data = await get_or_create_user(session, message.from_user)
    await message.answer(msg.welcome_message(user_data.full_name), reply_markup=kb.main_menu_keyboard())

# --- MAIN MENU & TOP-LEVEL ACTIONS ---
@main_router.callback_query(F.data == "order_number")
async def cq_order_number(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(msg.SELECT_NUMBER_TYPE, reply_markup=kb.number_type_keyboard())
    await state.set_state(OrderState.choosing_type)

@main_router.callback_query(F.data == "my_numbers")
async def cq_my_numbers(callback: CallbackQuery, session):
    await callback.answer()
    user_data = await get_or_create_user(session, callback.from_user)
    query = select(Number).where(Number.user_id == user_data.id, Number.status == "active").order_by(Number.created_at.desc())
    result = await session.execute(query)
    numbers = result.scalars().all()
    if not numbers:
        response_text = "📭 <b>You have no active numbers.</b>"
    else:
        response_text = "📱 <b>Your Active Numbers:</b>\n\n"
        for num in numbers:
            response_text += f"📞 <code>{num.phone_number}</code>\n   Service: {num.service_code.upper()}\n   Expires: {num.expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
    await callback.message.edit_text(response_text, reply_markup=kb.main_menu_keyboard())

@main_router.callback_query(F.data == "support")
async def cq_support(callback: CallbackQuery):
    await callback.answer()
    support_text = "🆘 <b>Help & Support</b>\n\n📧 <b>Email:</b>\n• info@numrow.com\n• gidatechnologies@gmail.com"
    await callback.message.edit_text(support_text, reply_markup=kb.main_menu_keyboard())

# --- UNIVERSAL BACK, PAGINATION, AND REFRESH ---
@main_router.callback_query(F.data.startswith(kb.CB_BACK))
async def cq_back_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    action = callback.data.split(':')[1]
    
    if action == "main_menu":
        await state.clear()
        await callback.message.edit_text(msg.welcome_message(callback.from_user.full_name), reply_markup=kb.main_menu_keyboard())
    elif action == "type_select":
        await cq_order_number(callback, state)
    elif action == "country_select":
        await callback.message.edit_text(msg.SELECT_COUNTRY, reply_markup=kb.initial_selection_keyboard("list_countries:", "start_search_country", f"{kb.CB_BACK}type_select"))
        await state.set_state(OrderState.choosing_country)
    elif action == "service_select":
        data = await state.get_data()
        await callback.message.edit_text(msg.SELECT_SERVICE, reply_markup=kb.initial_selection_keyboard("list_services:", "start_search_service", f"{kb.CB_BACK}country_select"))
        await state.set_state(OrderState.choosing_service)

@main_router.callback_query(F.data.startswith("load_more:"))
async def cq_load_more_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(':', 2)
    if len(parts) != 3: return

    _, prefix, offset_str = parts
    offset = int(offset_str)

    current_state = await state.get_state()
    
    if prefix == "country" and current_state == OrderState.choosing_country:
        await cq_show_countries(callback, state, offset=offset)
    elif prefix == "service" and current_state == OrderState.choosing_service:
        await cq_show_services(callback, state, offset=offset)

@main_router.callback_query(F.data.startswith("refresh_sms:"))
async def cq_refresh_sms(callback: CallbackQuery, session):
    """Handles the manual SMS refresh button."""
    try:
        number_db_id = int(callback.data.split(':')[1])
    except (ValueError, IndexError):
        await callback.answer("Invalid button data.", show_alert=True)
        return

    await callback.answer("Checking for new SMS...", show_alert=False)

    number_obj = await session.get(Number, number_db_id, options=[selectinload(Number.user)])
    if not number_obj or number_obj.user.telegram_id != callback.from_user.id:
        await callback.answer("This is not your number.", show_alert=True)
        return

    is_rent = False # Assume temp for now, needs logic to check if it's a rental
    
    countries = await pva_service.get_countries(is_rent=is_rent)
    country_name = next((c['name'] for c in countries if c['id'] == number_obj.country_code), None)
    
    if not country_name:
        await callback.answer("Error: Country not found for this number.", show_alert=True)
        return

    # Triggering the API call is enough. The background worker will pick up the result.
    await pva_service.get_sms(
        phone_number=number_obj.phone_number,
        service_id=number_obj.service_code,
        country_id=number_obj.country_code,
        country_name=country_name,
        is_rent=is_rent
    )

# --- FULL ORDER FLOW ---
@main_router.callback_query(OrderState.choosing_type, F.data.startswith(kb.CB_PREFIX_NUMBER_TYPE))
async def cq_type_selected(callback: CallbackQuery, state: FSMContext):
    is_rent = callback.data.split(':')[1] == 'rent'
    await state.update_data(is_rent=is_rent)
    await callback.message.edit_text(
        msg.SELECT_COUNTRY,
        reply_markup=kb.initial_selection_keyboard("list_countries:", "start_search_country", f"{kb.CB_BACK}type_select")
    )
    await state.set_state(OrderState.choosing_country)

# --- COUNTRY FLOW ---
async def cq_show_countries(callback: CallbackQuery, state: FSMContext, offset: int = 0):
    data = await state.get_data()
    all_countries = await pva_service.get_countries(is_rent=data.get('is_rent', False))
    paginated_countries = all_countries[offset : offset + LOAD_MORE_COUNT]
    reply_markup = kb.load_more_list_keyboard(items=paginated_countries, prefix=kb.CB_PREFIX_COUNTRY, offset=offset, total_count=len(all_countries), back_callback=f"{kb.CB_BACK}type_select")
    try: await callback.message.edit_text("Select a country:", reply_markup=reply_markup)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in e.message: await callback.answer()
        else: raise

@main_router.callback_query(OrderState.choosing_country, F.data.startswith("list_countries:"))
async def cq_list_countries(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await cq_show_countries(callback, state, offset=0)

@main_router.callback_query(OrderState.choosing_country, F.data == "start_search_country")
async def cq_start_search_country(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(msg.SEARCH_COUNTRY_PROMPT)
    await state.set_state(OrderState.searching_country)

@main_router.message(OrderState.searching_country)
async def process_country_search(message: Message, state: FSMContext):
    await message.answer("🔍 Searching...")
    search_query = message.text.lower().strip()
    data = await state.get_data()
    all_countries = await pva_service.get_countries(is_rent=data.get('is_rent', False))
    filtered = [c for c in all_countries if search_query in c['name'].lower()]
    await message.answer(f"Found {len(filtered)} results:" if filtered else msg.NO_RESULTS, reply_markup=kb.load_more_list_keyboard(filtered, kb.CB_PREFIX_COUNTRY, 0, len(filtered), f"{kb.CB_BACK}type_select"))

@main_router.callback_query(OrderState.choosing_country, F.data.startswith(kb.CB_PREFIX_COUNTRY))
async def cq_country_selected(callback: CallbackQuery, state: FSMContext):
    country_id = callback.data.split(':')[1]
    data = await state.get_data()
    is_rent = data.get('is_rent', False)
    all_countries = await pva_service.get_countries(is_rent)
    country_name = next((c['name'] for c in all_countries if c['id'] == country_id), None)
    if not country_name: return

    await state.update_data(country_id=country_id, country_name=country_name)
    await callback.message.edit_text(msg.SELECT_SERVICE, reply_markup=kb.initial_selection_keyboard("list_services:", "start_search_service", f"{kb.CB_BACK}country_select"))
    await state.set_state(OrderState.choosing_service)

# --- SERVICE FLOW ---
async def cq_show_services(callback: CallbackQuery, state: FSMContext, offset: int = 0):
    data = await state.get_data()
    all_services = await pva_service.get_services(data.get('country_id'), is_rent=data.get('is_rent', False))
    paginated_services = all_services[offset : offset + LOAD_MORE_COUNT]
    reply_markup = kb.load_more_list_keyboard(items=paginated_services, prefix=kb.CB_PREFIX_SERVICE, offset=offset, total_count=len(all_services), back_callback=f"{kb.CB_BACK}country_select")
    try: await callback.message.edit_text("Select a service:", reply_markup=reply_markup)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in e.message: await callback.answer()
        else: raise
            
@main_router.callback_query(OrderState.choosing_service, F.data.startswith("list_services:"))
async def cq_list_services(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await cq_show_services(callback, state, offset=0)

@main_router.callback_query(OrderState.choosing_service, F.data == "start_search_service")
async def cq_start_search_service(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(msg.SEARCH_SERVICE_PROMPT)
    await state.set_state(OrderState.searching_service)

@main_router.message(OrderState.searching_service)
async def process_service_search(message: Message, state: FSMContext):
    await message.answer("🔍 Searching...")
    search_query = message.text.lower().strip()
    data = await state.get_data()
    all_services = await pva_service.get_services(data.get('country_id'), is_rent=data.get('is_rent', False))
    filtered = [s for s in all_services if search_query in s['name'].lower()]
    await message.answer(f"Found {len(filtered)} results:" if filtered else msg.NO_RESULTS, reply_markup=kb.load_more_list_keyboard(filtered, kb.CB_PREFIX_SERVICE, 0, len(filtered), f"{kb.CB_BACK}country_select"))

@main_router.callback_query(OrderState.choosing_service, F.data.startswith(kb.CB_PREFIX_SERVICE))
async def cq_service_selected(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split(':', 1)[1]
    await state.update_data(service_id=service_id)
    await process_price_request(callback, state)
    
async def process_price_request(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(msg.FETCHING_PRICE)
    selections = await state.get_data()
    price, price_ref, duration = await pricing_worker.get_final_price(
        country_id=selections.get('country_id'), service_id=selections.get('service_id'),
        is_rent=selections.get('is_rent')
    )
    if not price:
        await callback.message.edit_text(msg.SERVICE_UNAVAILABLE, reply_markup=kb.main_menu_keyboard())
        await state.clear()
        return
    await callback.message.edit_text(msg.final_price_message(price, duration), reply_markup=kb.payment_keyboard(price_ref))
    await state.set_state(OrderState.confirming_price)

@main_router.callback_query(OrderState.confirming_price, F.data.startswith(kb.CB_PREFIX_PAY))
async def cq_pay_now(callback: CallbackQuery, state: FSMContext, session):
    await callback.answer("Creating payment link...", show_alert=False)
    price_ref = callback.data.split(':', 1)[1]
    user_data = await get_or_create_user(session, callback.from_user)
    selections = await state.get_data()
    price, _, __ = await pricing_worker.get_final_price(
        country_id=selections.get('country_id'), service_id=selections.get('service_id'),
        is_rent=selections.get('is_rent')
    )
    if not price: return await callback.message.answer(msg.SERVICE_UNAVAILABLE)
    payment_url = await payment_worker.create_payment_link(session, user_data.id, price, price_ref)
    if payment_url:
        await callback.message.edit_text(msg.payment_link_message(payment_url), reply_markup=kb.payment_link_keyboard(payment_url))
    else:
        await callback.message.answer(msg.GENERIC_ERROR)
