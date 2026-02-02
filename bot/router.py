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

# Define the states for the order process
class OrderState(StatesGroup):
    choosing_country = State()
    choosing_service = State()
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

# --- Main Menu Callback Handlers ---

@main_router.callback_query(F.data == "order_number")
async def cq_order_number(callback: CallbackQuery, state: FSMContext):
    """Starts the number ordering flow."""
    app_logger.info(f"User {callback.from_user.id} started order flow.")
    await callback.answer()

    mock_countries = [
        {'id': '0', 'name': '🇳🇬 Nigeria'},
        {'id': '1', 'name': '🇬🇭 Ghana'},
        {'id': '12', 'name': '🇺🇸 USA'},
        {'id': '2', 'name': '🇬🇧 UK'},
    ]

    await callback.message.edit_text(
        msg.SELECT_COUNTRY,
        reply_markup=kb.country_selection_keyboard(mock_countries)
    )
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

# --- Order Flow FSM Handlers ---

@main_router.callback_query(OrderState.choosing_country, F.data.startswith(kb.CB_PREFIX_COUNTRY))
async def cq_country_selected(callback: CallbackQuery, state: FSMContext):
    """Handles country selection."""
    country_id = callback.data.split(':')[1]
    await state.update_data(country_id=country_id)
    await callback.answer(f"Country selected.")
    app_logger.info(f"User {callback.from_user.id} selected country: {country_id}")

    mock_services = [
        {'id': 'wa', 'name': 'WhatsApp'},
        {'id': 'tg', 'name': 'Telegram'},
        {'id': 'fb', 'name': 'Facebook'},
        {'id': 'go', 'name': 'Google'},
    ]
    
    await callback.message.edit_text(
        msg.SELECT_SERVICE,
        reply_markup=kb.service_selection_keyboard(mock_services)
    )
    await state.set_state(OrderState.choosing_service)

@main_router.callback_query(OrderState.choosing_service, F.data.startswith(kb.CB_PREFIX_SERVICE))
async def cq_service_selected(callback: CallbackQuery, state: FSMContext):
    """Handles service selection."""
    service_id = callback.data.split(':')[1]
    await state.update_data(service_id=service_id)
    await callback.answer(f"Service selected.")
    app_logger.info(f"User {callback.from_user.id} selected service: {service_id}")

    await callback.message.edit_text(
        msg.SELECT_NUMBER_TYPE,
        reply_markup=kb.number_type_keyboard()
    )
    await state.set_state(OrderState.choosing_number_type)

@main_router.callback_query(OrderState.choosing_number_type, F.data.startswith(kb.CB_PREFIX_NUMBER_TYPE))
async def cq_type_selected(callback: CallbackQuery, state: FSMContext):
    """Handles number type selection and fetches the final price."""
    number_type = callback.data.split(':')[1]
    await state.update_data(number_type=number_type)
    
    user_selections = await state.get_data()
    app_logger.info(f"User {callback.from_user.id} completed selection: {user_selections}")

    await callback.message.edit_text(msg.FETCHING_PRICE)

    # Call the pricing worker
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
    """Handles the 'Pay Now' button click."""
    await callback.answer("Creating your payment link...")
    
    callback_parts = callback.data.split(':', 2)
    if len(callback_parts) < 3:
        await callback.message.answer(msg.GENERIC_ERROR)
        return
    
    payment_id_placeholder = callback_parts[1]
    price_ref = callback_parts[2]
    
    user_data = await get_or_create_user(session, callback.from_user)
    
    selections = await state.get_data()
    
    from workers.pricing_worker import get_final_ngn_price
    final_price_ngn, _ = await get_final_ngn_price(
        selections.get('country_id', '0'),
        selections.get('service_id', 'wa'),
        selections.get('number_type', 'temporary')
    )
    
    if not final_price_ngn:
        await callback.message.answer(msg.SERVICE_UNAVAILABLE)
        return
    
    from workers.payment_worker import create_payment_link
    
    payment_url = await create_payment_link(
        session=session,
        user_id=user_data.id,
        final_ngn_price=final_price_ngn,
        price_ref=price_ref
    )
    
    if payment_url:
        await callback.message.edit_text(
            msg.payment_link_message(payment_url),
            reply_markup=kb.payment_link_keyboard(payment_url)
        )
    else:
        await callback.message.answer(msg.GENERIC_ERROR)

# --- Cancel Handler ---
@main_router.callback_query(F.data.startswith(kb.CB_PREFIX_CANCEL))
async def cq_cancel_flow(callback: CallbackQuery, state: FSMContext):
    """Allows user to cancel and return to main menu."""
    await callback.answer("Operation cancelled.")
    await state.clear()
    
    await callback.message.edit_text(
        msg.welcome_message(callback.from_user.full_name),
        reply_markup=kb.main_menu_keyboard()
    )
