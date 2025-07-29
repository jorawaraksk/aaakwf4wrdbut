import re
import asyncio
from .utils import STS
from database import Db, db
from config import temp
from script import Script
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid, ChatAdminRequired, UsernameInvalid,
    UsernameNotModified, ChannelPrivate
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


@Client.on_message(filters.private & filters.command(["forward"]))
async def run(bot, message):
    buttons = []
    btn_data = {}
    user_id = message.from_user.id
    _bot = await db.get_bot(user_id)
    if not _bot:
        _bot = await db.get_userbot(user_id)
        if not _bot:
            return await message.reply("<code>You didn't added any bot. Please add a bot using /settings !</code>")

    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply_text("please set a to channel in /settings before forwarding")

    if len(channels) > 1:
        for channel in channels:
            buttons.append([KeyboardButton(f"{channel['title']}")])
            btn_data[channel['title']] = channel['chat_id']
        buttons.append([KeyboardButton("cancel")])
        _toid = await bot.ask(
            message.chat.id,
            Script.TO_MSG.format(_bot['name'], _bot['username']),
            reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
        )
        if _toid.text.startswith(('/', 'cancel')):
            return await message.reply_text(Script.CANCEL, reply_markup=ReplyKeyboardRemove())
        to_title = _toid.text
        toid = btn_data.get(to_title)
        if not toid:
            return await message.reply_text("wrong channel choosen !", reply_markup=ReplyKeyboardRemove())
    else:
        toid = channels[0]['chat_id']
        to_title = channels[0]['title']

    fromid = await bot.ask(message.chat.id, Script.FROM_MSG, reply_markup=ReplyKeyboardRemove())
    if fromid.text and fromid.text.startswith('/'):
        await message.reply(Script.CANCEL)
        return

    # Handle link input
    if fromid.text and not fromid.forward_origin.date:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(fromid.text.replace("?single", ""))
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
    elif fromid.forward_origin and getattr(fromid.forward_origin.chat, 'type', None) in [enums.ChatType.CHANNEL, 'supergroup']:
        origin = fromid.forward_origin
        last_msg_id = origin.message_id
        chat_obj = origin.chat
        chat_id = chat_obj.username or chat_obj.id
        if last_msg_id is None:
            return await message.reply_text(
                "**This may be a forwarded message from a group and sent by anonymous admin. Instead, please send the last message link from the group.**"
            )
    else:
        return await message.reply_text("**Invalid!**")

    try:
        title = (await bot.get_chat(chat_id)).title
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = "private" if fromid.text else fromid.forward_from_chat.title
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')

    skipno = await bot.ask(message.chat.id, Script.SKIP_MSG)
    if skipno.text.startswith('/'):
        await message.reply(Script.CANCEL)
        return

    forward_id = f"{user_id}-{skipno.id}"
    confirm_buttons = [
        [
            InlineKeyboardButton('Yes', callback_data=f"start_public_{forward_id}"),
            InlineKeyboardButton('No', callback_data="close_btn")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(confirm_buttons)
    await message.reply_text(
        text=Script.DOUBLE_CHECK.format(
            botname=_bot['name'],
            botuname=_bot['username'],
            from_chat=title,
            to_chat=to_title,
            skip=skipno.text
        ),
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )
    STS(forward_id).store(chat_id, toid, int(skipno.text), int(last_msg_id))
