import logging
import requests
import traceback
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, ChatMember, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
from telegram.error import BadRequest

TOKEN = "YOUR_BOT_TOKEN_HERE"

# Enable logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Dictionary to store user points
user_points = {}
referred_users = {}

# Helper function to check if a user has joined the channel
def check_user_joined_channel(user_id):
    logging.info("Entering check_user_joined_channel")
    token = "YOUR_BOT_TOKEN_HERE"
    channel_username = "YOUR_CHANNEL_USERNAME"

    url = f"https://api.telegram.org/bot{token}/getChatMember?chat_id=@{channel_username}&user_id={user_id}"
    response = requests.get(url).json()

    if response.get("ok") and response.get("result", {}).get("status") not in ["left", "kicked"]:
        return True
    else:
        return False

def add_point_to_referrer(referral_code, new_user_id, context):
    referral_user_id = int(referral_code)
    conn = sqlite3.connect('referral_points.db')
    c = conn.cursor()

    # Check if the referrer already exists in the database
    c.execute("SELECT * FROM referral_points WHERE user_id=?", (referral_user_id,))
    result = c.fetchone()

    if result:
        # Update points if the referrer exists
        c.execute("UPDATE referral_points SET points=points+1 WHERE user_id=?", (referral_user_id,))
    else:
        # Insert a new row for the referrer with 1 point
        c.execute("INSERT INTO referral_points (user_id, points) VALUES (?, ?)", (referral_user_id, 1))

    conn.commit()
    conn.close()

    context.bot.send_message(chat_id=referral_user_id, text="You've earned a point! A new user joined using your referral link.")

def create_database():
    conn = sqlite3.connect('user_points.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_points
                      (user_id INTEGER PRIMARY KEY, points INTEGER)''')
    conn.commit()
    conn.close()

create_database()

def setup_database():
    conn = sqlite3.connect('referral_points.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS referral_points
                 (user_id INTEGER PRIMARY KEY, points INTEGER)''')
    conn.commit()
    conn.close()

setup_database()

def redeem_menu(update_or_query, context):
    if isinstance(update_or_query, Update):
        chat_id = update_or_query.message.chat_id
    else:  # isinstance(update_or_query, CallbackQuery)
        chat_id = update_or_query.message.chat.id

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Netflix Account (10)", callback_data="redeem_account:10:Netflix Account")],
        [InlineKeyboardButton("Disney Account (10)", callback_data="redeem_disney:10:Disney Account")],
        [InlineKeyboardButton("Spotify Premium (20)", callback_data="redeem_spotify:20:Spotify Account")],
        [InlineKeyboardButton("YouTube Premium (10)", callback_data="redeem_youtube:10:Youtube Account")],
        [InlineKeyboardButton("Netflix On Your Mail (30)", callback_data="redeem_netflix_email:30:Netflix On Mail")],
        [InlineKeyboardButton("Prime On Your Mail (25)", callback_data="redeem_prime_email:25:Prime On Mail")],
        [InlineKeyboardButton("Telegram Premium (50)", callback_data="redeem_telegram_premium:30:Telegram Premium")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main_menu")],
    ])
    try:
        update_or_query.message.edit_text("🔄Exchange Point to ~", reply_markup=reply_markup)
    except BadRequest as e:
        if str(e) == "Message is not modified":
            pass
        else:
            raise

def is_user_in_channel(context: CallbackContext, user_id: int, channel_username: str) -> bool:
    try:
        chat_member = context.bot.get_chat_member(chat_id=channel_username, user_id=user_id)
        if chat_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
            return True
    except BadRequest:
        pass

    return False

def add_user_points(user_id, points):
    conn = sqlite3.connect('user_points.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO user_points (user_id, points) VALUES (?, ?)', (user_id, points))
    conn.commit()
    conn.close()

def update_user_points(user_id, points):
    conn = sqlite3.connect('user_points.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE user_points SET points = points + ? WHERE user_id = ?', (points, user_id))
    conn.commit()
    conn.close()

def get_user_points(user_id):
    conn = sqlite3.connect('user_points.db')
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM user_points WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    else:
        return 0

def my_account(update_or_query, context):
    try:
        if isinstance(update_or_query, Update):
            chat_id = update_or_query.message.chat_id
        else:  # isinstance(update_or_query, CallbackQuery)
            chat_id = update_or_query.message.chat.id

        user_id = update_or_query.message.from_user.id

        # Fetch user points from the user_points dictionary
        user_points_value = user_points.get(user_id, 0)

        message = f"📊 Your Points: {user_points_value} Press /start to return"

        try:
            update_or_query.message.edit_text(message)
        except BadRequest as e:
            if str(e) == "Message is not modified":
                pass
            else:
                raise
    except Exception as e:
        logging.error(f"Error in my_account: {e}")
        logging.debug(traceback.format_exc())
        try:
            update_or_query.message.edit_text("An error occurred. Please try again.")
        except BadRequest as e:
            if str(e) != "Message is not modified":
                raise


def back_to_main_menu(query, context):
    main_menu(query, context)

def invite(update_or_query, context):
    if isinstance(update_or_query, Update):
        chat_id = update_or_query.message.chat_id
    else:  # isinstance(update_or_query, CallbackQuery)
        chat_id = update_or_query.message.chat.id

    user_id = update_or_query.from_user.id

    # Generate a unique referral link for the user
    invite_link = f"https://t.me/USERNAME_OF_BOT?start={user_id}"

    message = f"📩 Invite your friends to join our bot using the following link:\n\n{invite_link}"

    if isinstance(update_or_query, Update):
        update_or_query.message.reply_text(message)
    else:  # isinstance(update_or_query, CallbackQuery)
        update_or_query.message.edit_text(message)

def welcome_menu(update, context):
    chat_id = update.effective_chat.id

    # Create InlineKeyboardButtons with corresponding callback_data
    points_button = InlineKeyboardButton("📊 Points", callback_data="points")
    redeem_button = InlineKeyboardButton("🔄 Redeem", callback_data="redeem")
    invite_button = InlineKeyboardButton("📩 Invite", callback_data="invite_link")

    # Create an InlineKeyboardMarkup and add the InlineKeyboardButtons to it
    keyboard = InlineKeyboardMarkup(
        [
            [points_button, redeem_button],
            [invite_button]
        ]
    )

    # Send the message with the inline keyboard attached
    context.bot.send_message(chat_id=chat_id, text="Welcome to the Rewards Bot! Choose an option:", reply_markup=keyboard)

def handle_message(update: Update, context: CallbackContext):
    message_text = update.message.text

    if message_text == "📊 Points":
        my_account(update, context)
    elif message_text == "🔄 Redeem":
        redeem_menu(update, context)
    elif message_text == "📩 Invite":
        invite(update, context)


def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_name = update.effective_user.username or update.effective_user.first_name
    channel_username = '@channel_username'  # Replace with your channel's username

    if not is_user_in_channel(context, user_id, channel_username):
        text = f"Welcome, {user_name}! To use this bot, you must join our channel first. And use /start again."
        keyboard = [
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{channel_username[1:]}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)
        return

    text = f"Welcome, {user_name}! You have successfully started the bot."

    # Check if the message text contains a referral code
    referral_code = update.message.text[7:]
    if referral_code:
        try:
            referral_code = int(referral_code)
            if user_id != referral_code:
                add_point_to_referrer(referral_code, user_id, context)  # Pass user_id and context as parameters here
            else:
                text += "\n\nYou cannot use your own referral code."
        except ValueError:
            text += "\n\nInvalid referral code."

    context.bot.send_message(chat_id=user_id, text=text)

    welcome_menu(update,context)

def points(query, context: CallbackContext):
    user_id = query.from_user.id
    points = user_points.get(user_id, 0)
    query.message.reply_text(f"You have {points} points.")

def check_membership_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if check_user_joined_channel(user_id):
        query.delete_message()
        welcome_menu(query, context)
    else:
        query.answer("You haven't joined the channel yet. Please join the channel and try again.")

def error_handler(update: Update, context: CallbackContext):
    """Log the error and send a message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logging.error(msg="Exception while handling an update:", exc_info=context.error)
    
    # Replace CHAT_ID with the chat ID of the person you want to notify.
    context.bot.send_message(chat_id=YOUR_CHAT_ID, text="An error occurred. Check the logs for more information.")

def join_message(update_or_query, context: CallbackContext):
    channel_url = "YOUR_TELEGRAM_CHANNEL_URL"

    keyboard = [
        [
            InlineKeyboardButton("Join", url=channel_url)
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    if isinstance(update_or_query, Update):
        update_or_query.message.reply_text(
            "You must join our channel to use this bot. Click the button below to join:",
            reply_markup=reply_markup
        )
    elif isinstance(update_or_query, CallbackQuery):
                update_or_query.message.chat.send_message(
           "You must join our channel to use this bot. Click the button below to join:",
            reply_markup=reply_markup
        )

def main_menu(query, context):
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Points", callback_data="points")],
        [InlineKeyboardButton("🔄 Redeem", callback_data="redeem")],
        [InlineKeyboardButton("📩 Invite", callback_data="invite_link")],
    ])
    query.message.edit_text("Welcome to the main menu!", reply_markup=reply_markup)

def redeem_account(query, context, *args):
    cost = int(args[0])  # Get cost from args
    item_name = args[1]  # Get item_name from args

    user_id = query.from_user.id

    points = get_user_points(user_id)

    if points >= cost:
        # Add the functionality to generate the requested account
        update_user_points(user_id, points - cost)
        query.edit_message_text(f"Here is your {item_name}:\n\n{generate_account(item_name)}")
    else:
        query.answer("Not enough points.")

def handle_callback_query(update: Update, context: CallbackContext):
    logging.info("Entering handle_callback_query")
    query = update.callback_query
    data = query.data
    action, *args = data.split(":")

    try:
        logging.info(f"Trying to process action: {action}")
        if action in callback_mapping:
            callback_mapping[action](query, context, *args)
        else:
            query.message.edit_text("An error occurred. Please try again.")
    except Exception as e:
        logging.error(f"An error occurred while processing the callback query: {e}")
        logging.error(traceback.format_exc())
        query.message.edit_text("An error occurred. Please try again.")

def redeem_account_callback(query, context):
    data = query.data

    if data == "redeem_netflix":
        redeem_account(query, context, 10, "Netflix Account")
    elif data == "redeem_disney":
        redeem_account(query, context, 10, "Disney Account")
    elif data == "redeem_spotify":
        redeem_account(query, context, 20, "Spotify Premium")
    elif data == "redeem_youtube":
        redeem_account(query, context, 10, "YouTube Premium")
    elif data == "redeem_netflix_email":
        redeem_account(query, context, 30, "Netflix On Your Mail")
    elif data == "redeem_prime_email":
        redeem_account(query, context, 25, "Prime On Your Mail")
    elif data == "redeem_telegram_premium":
        redeem_account(query, context, 50, "Telegram Premium")
    else:
        query.message.edit_text("An error occurred. Please try again.")

callback_mapping = {
    "redeem": redeem_menu,
    "points": my_account,
    "invite_link": invite,
    "back_to_main_menu": main_menu,
    "redeem_account": redeem_account,
    "redeem_disney": redeem_account,
    "redeem_spotify": redeem_account,
    "redeem_youtube": redeem_account,
    "redeem_netflix_email": redeem_account,
    "redeem_prime_email": redeem_account,
    "redeem_telegram_premium": redeem_account,
}

def get_dispatcher():
    updater = Updater(TOKEN)
    return updater.dispatcher

# Register the error handler with the dispatcher.
dispatcher = get_dispatcher()
dispatcher.add_error_handler(error_handler)

def main():
    updater = Updater("YOUR_BOT_TOKEN_HERE", use_context=True)

    dp = updater.dispatcher

    # Register the error handler with the dispatcher inside the main() function
    dp.add_error_handler(error_handler)
    dp.add_handler(CallbackQueryHandler(check_membership_callback, pattern="^check_membership$"))

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_callback_query))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    logger.info("Starting the bot")
    main()