from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from service import create_message, get_messages_to_page
from buttons import paginate_buttons


router = Router()


@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    messages = await get_messages_to_page(state)
    await message.answer(messages, reply_markup=paginate_buttons())


@router.callback_query(F.data == '1')
async def page_down(call, state: FSMContext):
    messages = await get_messages_to_page(state, 'down')
    await call.message.answer(messages, reply_markup=paginate_buttons())


@router.callback_query(F.data == '2')
async def page_up(call, state: FSMContext):
    messages = await get_messages_to_page(state, 'up')
    await call.message.answer(messages, reply_markup=paginate_buttons())


@router.message()
async def echo_handler(message: Message, state: FSMContext) -> None:
    await create_message(message.from_user.full_name, message.text, message.date, state)
