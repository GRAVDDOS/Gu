import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, Text
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "7868284104:AAGTYxuHZxlaj39NY3qYDR0HvHPa86vQx0g"  # Replace with your bot token
ADMIN_ID = 1441704343  # Replace with your Telegram ID

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# --- SQLite DB ---
conn = sqlite3.connect("mines_bot.db")
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)''')
conn.commit()

# --- Helper Functions ---
def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def update_balance(user_id, amount):
    current = get_balance(user_id)
    if current == 0 and amount >= 0:
        cursor.execute("INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)", (user_id, amount))
    else:
        cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (current + amount, user_id))
    conn.commit()

def generate_grid(mines_count):
    positions = random.sample(range(25), mines_count)
    grid = ['⬜' for _ in range(25)]
    for pos in positions:
        grid[pos] = '💣'
    return grid

def render_grid(grid, revealed):
    view = ""
    for i in range(25):
        if revealed[i]:
            view += grid[i] if grid[i] == '💣' else '💎'
        else:
            view += '⬜'
        if (i + 1) % 5 == 0:
            view += "\n"
    return view

# --- Handlers ---
@dp.message(Command("start"))
async def start(msg: types.Message):
    update_balance(msg.from_user.id, 0)
    await msg.answer("Welcome to Mines Game Bot!\nUse /balance to check your balance.\nUse /play to start playing!")

@dp.message(Command("balance"))
async def balance(msg: types.Message):
    bal = get_balance(msg.from_user.id)
    await msg.answer(f"💰 Your balance: <b>{bal}</b>")

@dp.message(Command("add_balance"))
async def add_balance(msg: types.Message):
    await msg.answer("Send your UPI payment screenshot here. It will be forwarded to admin for approval.")
    
@dp.message(Command("play"))
async def play(msg: types.Message):
    await msg.answer("Enter amount to bet:")

    @dp.message()
    async def get_bet(m: types.Message):
        try:
            bet = int(m.text)
            bal = get_balance(m.from_user.id)
            if bet <= 0 or bet > bal:
                await m.answer("Invalid bet amount.")
                return

            await m.answer("Enter number of mines (e.g. 3, 5, 10):")

            @dp.message()
            async def get_mines(m2: types.Message):
                try:
                    mines = int(m2.text)
                    if mines >= 25 or mines < 1:
                        await m2.answer("Invalid number of mines.")
                        return

                    update_balance(m.from_user.id, -bet)
                    grid = generate_grid(mines)
                    revealed = [False]*25

                    kb = InlineKeyboardBuilder()
                    for i in range(25):
                        kb.button(text=str(i+1), callback_data=f"reveal_{i}_{bet}_{mines}")
                    kb.adjust(5)

                    await m2.answer(f"Game Started!\nTap to reveal tiles.\n💣 Mines: {mines}\n💰 Bet: {bet}", reply_markup=kb.as_markup())
                except:
                    await m2.answer("Invalid number.")
        except:
            await m.answer("Please send a valid number.")

@dp.callback_query(Text(startswith="reveal_"))
async def reveal_tile(callback: types.CallbackQuery):
    data = callback.data.split("_")
    index = int(data[1])
    bet = int(data[2])
    mines = int(data[3])
    
    user_data = callback.message.reply_markup.inline_keyboard
    grid = generate_grid(mines)
    revealed = [False]*25
    revealed[index] = True

    if grid[index] == '💣':
        await callback.message.edit_text(f"💥 You hit a mine!\n\n{render_grid(grid, revealed)}\n\nYou lost <b>{bet}</b> coins.")
    else:
        reward = bet * 2
        update_balance(callback.from_user.id, reward)
        await callback.message.edit_text(f"✅ You found a gem!\n\n{render_grid(grid, revealed)}\n\nYou won <b>{reward}</b> coins!")

@dp.message()
async def forward_to_admin(msg: types.Message):
    if msg.photo:
        await msg.forward(ADMIN_ID)
        await msg.answer("Screenshot sent to admin for approval.")
    else:
        await msg.answer("Unknown command. Use /play to start Mines game.")

# --- Main ---
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
