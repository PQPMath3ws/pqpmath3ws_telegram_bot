from commands import Commands
from database import Database
from dotenv import load_dotenv
from os import getenv
from telegram.ext import ApplicationBuilder

bot = None
db = None


def init_database() -> None:
    global db
    db = Database(db_file="bot_db.db")
    db.initDatabase()


def close_database() -> None:
    global bot, db
    db.closeDatabase()
    bot = None
    db = None


def init_and_start_bot(
    client_id: str, secret_key: str, proposal_chat_id: int, owner_user_id: int
):
    global db, bot
    bot = ApplicationBuilder().token(token=f"{client_id}:{secret_key}").build()
    commands = Commands(
        bot=bot, db=db, proposal_chat_id=proposal_chat_id, owner_user_id=owner_user_id
    )
    commands.apply_commands()
    bot.run_polling()


def init():
    load_dotenv()
    BOT_CLIENT_ID: str | None = getenv(key="BOT_CLIENT_ID")
    BOT_SECRET_KEY: str | None = getenv(key="BOT_SECRET_KEY")
    PROPOSALS_CHAT_ID: int = int(getenv(key="PROPOSALS_CHAT_ID"))
    OWNER_USER_ID: int = int(getenv(key="OWNER_USER_ID"))
    if (
        BOT_CLIENT_ID is None
        and BOT_SECRET_KEY is None
        and PROPOSALS_CHAT_ID is None
        and OWNER_USER_ID is None
    ):
        exit()
    init_database()
    init_and_start_bot(
        client_id=BOT_CLIENT_ID,
        secret_key=BOT_SECRET_KEY,
        proposal_chat_id=PROPOSALS_CHAT_ID,
        owner_user_id=OWNER_USER_ID,
    )
    close_database()


try:
    if __name__ == "__main__":
        init()
except KeyboardInterrupt:
    if db is not None:
        close_database()
