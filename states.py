from aiogram.fsm.state import State, StatesGroup


class Flow(StatesGroup):
    waiting_birthdate = State()
    waiting_desire = State()
    waiting_bracelet_decision = State()
    waiting_size = State()
    waiting_metal = State()
    waiting_intention = State()
    waiting_package = State()
    waiting_address = State()
    waiting_payment = State()
    waiting_screenshot = State()
    waiting_admin_review = State()


class Encyclopedia(StatesGroup):
    menu = State()
    stone = State()
