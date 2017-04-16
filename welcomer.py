# -*- coding: utf-8 -*-

import asyncio
import logging
import sqlite3
from datetime import datetime
from pprint import pprint

import aiohttp
import telepot
import telepot.aio

import config

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(config.bot_username)
bot = telepot.aio.Bot(config.bot_token)

welcome_message = "Привет!"
message_count = 0
timeout = False


async def switch_welcome_message():
    global welcome_message
    current_hour = datetime.now().hour()
    if 0 > current_hour > 6:
        welcome_message = "Доброй ночи, неспящий человек!"
    elif 6 > current_hour > 10:
        welcome_message = "Доброго утра!"
    elif 10 > current_hour > 17:
        welcome_message = "Доброго дня!"
    elif 17 > current_hour >= 23:
        welcome_message = "Доброго вечера!"
    await asyncio.sleep(60 * 60)


async def set_timeout():
    global timeout
    await asyncio.sleep(60 * 15)
    timeout = False


async def welcome_user(username, msg_id):
    global message_count, timeout
    if not timeout:
        while message_count < 7:
            await asyncio.sleep(0.1)
        if message_count >= 7:
            await bot.sendMessage(chat_id=1,  # Your chat id
                                  text=f"{welcome_message}, {username}! "
                                       f"Расскажи немного о себе в реплае на это сообщение!",
                                  reply_to_message_id=msg_id)
            message_count = 0
    else:
        timeout = True
        await set_timeout()
        await bot.sendMessage(chat_id=1,  # Your chat id
                              text=f"{welcome_message}, {username}! Расскажи немного о себе в реплае на это сообщение!",
                              reply_to_message_id=msg_id)


async def handle(msg):
    global message_count
    content_type, chat_type, chat_id = telepot.glance(msg)
    pprint(msg)
    if 'new_chat_member' in msg:
        if 'username' in msg['new_chat_member']:
            await welcome_user("@" + msg['new_chat_member']['username'],
                               msg['message_id'])
        elif 'last_name' in msg['new_chat_member']:
            await welcome_user(msg['new_chat_member']['first_name'] + " " + msg['new_chat_member']['last_name'],
                               msg['message_id'])
        else:
            await welcome_user(msg['new_chat_member']['first_name'],
                               msg['message_id'])
    else:
        message_count += 1
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
          f"Chat: {content_type} {chat_type} {chat_id}\n")


def main():
    loop = asyncio.get_event_loop()

    loop.create_task(switch_welcome_message())
    loop.create_task(bot.message_loop(handle))

    loop.run_forever()


if __name__ == "__main__":
    main()
