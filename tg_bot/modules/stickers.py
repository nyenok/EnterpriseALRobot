import hashlib
import os
import math
import re
import requests
import urllib.request as urllib

from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup as bs

from typing import Optional, List
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import TelegramError
from telegram import Update, Bot
from telegram.ext import CommandHandler, run_async
from telegram.utils.helpers import escape_markdown

from tg_bot import dispatcher

from tg_bot.modules.disable import DisableAbleCommandHandler

combot_stickers_url = "https://combot.org/telegram/stickers?q="

@run_async
def stickerid(bot: Bot, update: Update):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        update.effective_message.reply_text(
            "Sticker ID:\n```"
            + escape_markdown(msg.reply_to_message.sticker.file_id)
            + "```",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        update.effective_message.reply_text("Harap balas stiker untuk mendapatkan ID-nya.")


@run_async
def cb_sticker(bot: Bot, update: Update):
    msg = update.effective_message
    split = msg.text.split(' ', 1)
    if len(split) == 1:
        msg.reply_text('Berikan beberapa nama untuk mencari paket.')
        return
    text = requests.get(combot_stickers_url + split[1]).text
    soup = bs(text, 'lxml')
    results = soup.find_all("a", {'class': "sticker-pack__btn"})
    titles = soup.find_all("div", "sticker-pack__title")
    if not results:
        msg.reply_text('Tidak ada hasil yang ditemukan :(.')
        return
    reply = f"Stickers for *{split[1]}*:"
    for result, title in zip(results, titles):
        link = result['href']
        reply += f"\n• [{title.get_text()}]({link})"
    msg.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

@run_async
def getsticker(bot: Bot, update: Update):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        file_id = msg.reply_to_message.sticker.file_id
        newFile = bot.get_file(file_id)
        newFile.download("sticker.png")
        bot.send_document(chat_id, document=open("sticker.png", "rb"))
        os.remove("sticker.png")
    else:
        update.effective_message.reply_text(
            "Harap balas stiker agar saya dapat mengupload PNG."
        )


@run_async
def steal(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    user = update.effective_user
    packnum = 0
    packname = "a" + str(user.id) + "_by_" + bot.username
    packname_found = 0
    max_stickers = 120
    while packname_found == 0:
        try:
            stickerset = bot.get_sticker_set(packname)
            if len(stickerset.stickers) >= max_stickers:
                packnum += 1
                packname = (
                    "a" + str(packnum) + "_" + str(user.id) + "_by_" + bot.username
                )
            else:
                packname_found = 1
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                packname_found = 1
    stolensticker = "stolensticker.png"
    if msg.reply_to_message:
        if msg.reply_to_message.sticker:
            file_id = msg.reply_to_message.sticker.file_id
        elif msg.reply_to_message.photo:
            file_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.document:
            file_id = msg.reply_to_message.document.file_id
        else:
            msg.reply_text("Yea, I can't steal that.")
        stolen_file = bot.get_file(file_id)
        stolen_file.download("stolensticker.png")
        if args:
            sticker_emoji = str(args[0])
        elif msg.reply_to_message.sticker and msg.reply_to_message.sticker.emoji:
            sticker_emoji = msg.reply_to_message.sticker.emoji
        else:
            sticker_emoji = "🤔"
        try:
            im = Image.open(stolensticker)
            maxsize = (512, 512)
            if (im.width and im.height) < 512:
                size1 = im.width
                size2 = im.height
                if im.width > im.height:
                    scale = 512 / size1
                    size1new = 512
                    size2new = size2 * scale
                else:
                    scale = 512 / size2
                    size1new = size1 * scale
                    size2new = 512
                size1new = math.floor(size1new)
                size2new = math.floor(size2new)
                sizenew = (size1new, size2new)
                im = im.resize(sizenew)
            else:
                im.thumbnail(maxsize)
            if not msg.reply_to_message.sticker:
                im.save(stolensticker, "PNG")
            bot.add_sticker_to_set(
                user_id=user.id,
                name=packname,
                png_sticker=open("stolensticker.png", "rb"),
                emojis=sticker_emoji,
            )
            msg.reply_text(
                f"Stiker berhasil ditambahkan ke [pack](t.me/addstickers/{packname})"
                + f"\nEmoji: {sticker_emoji}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except OSError as e:
            msg.reply_text("Saya hanya bisa mencuri gambar, bung.")
            print(e)
            return
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                makepack_internal(
                    msg,
                    user,
                    open("stolensticker.png", "rb"),
                    sticker_emoji,
                    bot,
                    packname,
                    packnum,
                )
            elif e.message == "Sticker_png_dimensions":
                im.save(stolensticker, "PNG")
                bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    png_sticker=open("stolensticker.png", "rb"),
                    emojis=sticker_emoji,
                )
                msg.reply_text(
                    f"Stiker berhasil ditambahkan ke [pack](t.me/addstickers/{packname})"
                    + f"\nEmoji: {sticker_emoji}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif e.message == "Invalid sticker emojis":
                msg.reply_text("Emoji tidak valid.")
            elif e.message == "Stickers_too_much":
                msg.reply_text("Ukuran paket maks tercapai.")
            elif e.message == "Internal Server Error: sticker set not found (500)":
                msg.reply_text(
                    "Stiker berhasil ditambahkan ke [pack](t.me/addstickers/%s)"
                    % packname
                    + "\n"
                    "Emoji:" + " " + sticker_emoji,
                    parse_mode=ParseMode.MARKDOWN,
                )
            print(e)
    elif args:
        try:
            try:
                urlemoji = msg.text.split(" ")
                png_sticker = urlemoji[1]
                sticker_emoji = urlemoji[2]
            except IndexError:
                sticker_emoji = "🤔"
            urllib.urlretrieve(png_sticker, stolensticker)
            im = Image.open(stolensticker)
            maxsize = (512, 512)
            if (im.width and im.height) < 512:
                size1 = im.width
                size2 = im.height
                if im.width > im.height:
                    scale = 512 / size1
                    size1new = 512
                    size2new = size2 * scale
                else:
                    scale = 512 / size2
                    size1new = size1 * scale
                    size2new = 512
                size1new = math.floor(size1new)
                size2new = math.floor(size2new)
                sizenew = (size1new, size2new)
                im = im.resize(sizenew)
            else:
                im.thumbnail(maxsize)
            im.save(stolensticker, "PNG")
            msg.reply_photo(photo=open("stolensticker.png", "rb"))
            bot.add_sticker_to_set(
                user_id=user.id,
                name=packname,
                png_sticker=open("stolensticker.png", "rb"),
                emojis=sticker_emoji,
            )
            msg.reply_text(
                f"Stiker berhasil ditambahkan ke [pack](t.me/addstickers/{packname})"
                + f"\nEmoji: {sticker_emoji}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except OSError as e:
            msg.reply_text("Saya hanya bisa mencuri gambar, bung.")
            print(e)
            return
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                makepack_internal(
                    msg,
                    user,
                    open("stolensticker.png", "rb"),
                    sticker_emoji,
                    bot,
                    packname,
                    packnum,
                )
            elif e.message == "Sticker_png_dimensions":
                im.save(stolensticker, "PNG")
                bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    png_sticker=open("stolensticker.png", "rb"),
                    emojis=sticker_emoji,
                )
                msg.reply_text(
                    "Stiker berhasil ditambahkan ke [pack](t.me/addstickers/%s)"
                    % packname
                    + "\n"
                    + "Emoji:"
                    + " "
                    + sticker_emoji,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif e.message == "Invalid sticker emojis":
                msg.reply_text("Emoji tidak valid.")
            elif e.message == "Stickers_too_much":
                msg.reply_text("Ukuran paket maks tercapai.")
            elif e.message == "Internal Server Error: sticker set not found (500)":
                msg.reply_text(
                    "Stiker berhasil ditambahkan ke [pack](t.me/addstickers/%s)"
                    % packname
                    + "\n"
                    "Emoji:" + " " + sticker_emoji,
                    parse_mode=ParseMode.MARKDOWN,
                )
            print(e)
    else:
        packs = "Harap balas stiker atau gambar untuk mencurinya ke paket Anda!\nOh, ngomong-ngomong, ini paket Anda:\n"
        if packnum > 0:
            firstpackname = "a" + str(user.id) + "_by_" + bot.username
            for i in range(0, packnum + 1):
                if i == 0:
                    packs += f"[pack](t.me/addstickers/{firstpackname})\n"
                else:
                    packs += f"[pack{i}](t.me/addstickers/{packname})\n"
        else:
            packs += f"[pack](t.me/addstickers/{packname})"
        msg.reply_text(packs, parse_mode=ParseMode.MARKDOWN)
    if os.path.isfile("stolensticker.png"):
        os.remove("stolensticker.png")


def makepack_internal(msg, user, png_sticker, emoji, bot, packname, packnum):
    name = user.first_name
    name = name[:50]
    try:
        extra_version = ""
        if packnum > 0:
            extra_version = " " + str(packnum)
        success = bot.create_new_sticker_set(
            user.id,
            packname,
            f"{name}'s Sticker Pack" + extra_version,
            png_sticker=png_sticker,
            emojis=emoji,
        )
    except TelegramError as e:
        print(e)
        if e.message == "Nama set stiker sudah dipakai":
            msg.reply_text(
                "Paket Anda dapat ditemukan [here](t.me/addstickers/%s)" % packname,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif e.message == "Peer_id_invalid":
            msg.reply_text(
                "Hubungi saya di PM dulu.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="Start", url=f"t.me/{bot.username}")]]
                ),
            )
        elif e.message == "Internal Server Error: created sticker set not found (500)":
            msg.reply_text(
                "Paket stiker berhasil dibuat! Mendapatkan [here](t.me/addstickers/%s)"
                % packname,
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    if success:
        msg.reply_text(
            "Paket stiker berhasil dibuat! Mendapatkan [here](t.me/addstickers/%s)"
            % packname,
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        msg.reply_text("Gagal membuat paket stiker.")


STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)
STEAL_HANDLER = DisableAbleCommandHandler(
    "steal", steal, pass_args=True, admin_ok=False
)
STICKERS_HANDLER = DisableAbleCommandHandler("stickers", cb_sticker)

dispatcher.add_handler(STICKERID_HANDLER)
dispatcher.add_handler(GETSTICKER_HANDLER)
dispatcher.add_handler(STEAL_HANDLER)
dispatcher.add_handler(STICKERS_HANDLER)
