import datetime
from typing import List

import requests
from telegram import Bot, Update, ParseMode
from telegram.ext import run_async

from tg_bot import dispatcher, TIME_API_KEY
from tg_bot.modules.disable import DisableAbleCommandHandler


def generate_time(to_find: str, findtype: List[str]) -> str:
    data = requests.get(
        f"http://api.timezonedb.com/v2.1/list-time-zone"
        f"?key={TIME_API_KEY}"
        f"&format=json"
        f"&fields=countryCode,countryName,zoneName,gmtOffset,timestamp,dst"
    ).json()

    for zone in data["zones"]:
        for eachtype in findtype:
            if to_find in zone[eachtype].lower():
                country_name = zone["countryName"]
                country_zone = zone["zoneName"]
                country_code = zone["countryCode"]

                if zone["dst"] == 1:
                    daylight_saving = "Yes"
                else:
                    daylight_saving = "No"

                date_fmt = r"%d-%m-%Y"
                time_fmt = r"%H:%M:%S"
                day_fmt = r"%A"
                gmt_offset = zone["gmtOffset"]
                timestamp = datetime.datetime.now(
                    datetime.timezone.utc
                ) + datetime.timedelta(seconds=gmt_offset)
                current_date = timestamp.strftime(date_fmt)
                current_time = timestamp.strftime(time_fmt)
                current_day = timestamp.strftime(day_fmt)

                break

    try:
        result = (
            f"<b>Negara :</b> <code>{country_name}</code>\n"
            f"<b>Nama Zona :</b> <code>{country_zone}</code>\n"
            f"<b>Kode negara :</b> <code>{country_code}</code>\n"
            f"<b>Daylight saving :</b> <code>{daylight_saving}</code>\n"
            f"<b>DHariay :</b> <code>{current_day}</code>\n"
            f"<b>Waktu saat ini :</b> <code>{current_time}</code>\n"
            f"<b>Tanggal sekarang :</b> <code>{current_date}</code>"
        )
    except:
        result = None

    return result


@run_async
def gettime(bot: Bot, update: Update):
    message = update.effective_message

    try:
        query = message.text.strip().split(" ", 1)[1]
    except:
        message.reply_text("Berikan nama negara/singkatan/zona waktu untuk ditemukan.")
        return
    send_message = message.reply_text(
        f"Menemukan info zona waktu untu <b>{query}</b>", parse_mode=ParseMode.HTML
    )

    query_timezone = query.lower()
    if len(query_timezone) == 2:
        result = generate_time(query_timezone, ["countryCode"])
    else:
        result = generate_time(query_timezone, ["zoneName", "countryName"])

    if not result:
        send_message.edit_text(
            f"Info zona waktu tidak tersedia untuk <b>{query}</b>", parse_mode=ParseMode.HTML
        )
        return

    send_message.edit_text(result, parse_mode=ParseMode.HTML)


TIME_HANDLER = DisableAbleCommandHandler("time", gettime)

dispatcher.add_handler(TIME_HANDLER)

__command_list__ = ["time"]
__handlers__ = [TIME_HANDLER]
