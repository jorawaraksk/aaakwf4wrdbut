import asyncio
import re
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import FloodWait, MessageNotModified
from .utils import STS
from database import Db, db
from config import temp
from script import Script

@Client.on_callback_query(filters.regex("^start_public_"))
async def start_forward(bot, query: CallbackQuery):
    forward_id = query.data.split("_")[-1]
    sts = STS(forward_id)
    user_id = int(forward_id.split("-")[0])

    data = sts.get_all()
    if not data:
        return await query.message.edit("**Session expired or already forwarded!**")

    from_chat, to_chat, skip_no, last_msg_id = data
    await query.message.edit("**Forwarding started...**")

    try:
        user_db = await db.get_userbot(user_id)
        session = user_db.get("session")
        name = user_db.get("name")
        if not session:
            return await query.message.edit("**User session not found. Add one with /settings**")
        client = Client(name, api_id=temp.API_ID, api_hash=temp.API_HASH, session_string=session)
    except Exception:
        return await query.message.edit("**Something went wrong while starting session.**")

    await client.start()

    try:
        async for msg in iter_messages(client, from_chat, last_msg_id):
            if msg == "FILTERED":
                continue

            if getattr(msg, "empty", False):
                continue

            try:
                await bot.copy_message(chat_id=to_chat, from_chat_id=msg.chat.id, message_id=msg.id)
                await asyncio.sleep(1)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except MessageNotModified:
                pass
            except Exception as e:
                print(f"Error while forwarding message {msg.id}: {e}")

        await query.message.edit("**Forwarding completed successfully!**")
    except Exception as e:
        await query.message.edit(f"**Error during forwarding:** `{e}`", reply_markup=retry_btn(forward_id))
    finally:
        await client.stop()
        sts.clear()


def retry_btn(id):
    return InlineKeyboardMarkup([[InlineKeyboardButton('♻️ RETRY ♻️', callback_data=f"start_public_{id}")]])


async def msg_edit(msg, text, reply_markup=None, disable_preview=False):
    try:
        await msg.edit(text=text, reply_markup=reply_markup, disable_web_page_preview=disable_preview)
    except MessageNotModified:
        pass


async def iter_messages(client, chat_id, limit):
    current = 0
    while True:
        new_diff = min(200, limit - current)
        if new_diff <= 0:
            return

        try:
            messages = await client.get_messages(chat_id, list(range(current + 1, current + new_diff + 1)))
        except Exception as e:
            print(f"Message fetching error: {e}")
            return

        for message in messages:
            if not message:
                continue

            filters_config = await db.get_configs(client.me.id)
            keywords = filters_config.get("keywords", [])
            extensions = filters_config.get("extension", [])
            min_size = filters_config.get("min_size", 0)
            max_size = filters_config.get("max_size", 999999999)

            if any(
                getattr(message, media_type, None)
                for media_type in ["photo", "video", "document"]
            ):
                if hasattr(message, "document"):
                    file_size = message.document.file_size
                    if file_size < min_size or file_size > max_size:
                        continue

                    if extensions and not any(message.document.file_name.lower().endswith(ext.lower()) for ext in extensions):
                        continue

                elif hasattr(message, "video"):
                    file_size = message.video.file_size
                    if file_size < min_size or file_size > max_size:
                        continue

                    if extensions and not any(message.video.file_name.lower().endswith(ext.lower()) for ext in extensions):
                        continue

                elif hasattr(message, "photo"):
                    pass  # no size or extension check on photos

                if keywords:
                    text = message.caption or ""
                    if not any(keyword.lower() in text.lower() for keyword in keywords):
                        continue

                yield message
            else:
                yield "FILTERED"

            current += 1
