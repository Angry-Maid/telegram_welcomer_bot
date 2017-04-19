# -*- coding: utf-8 -*-

import asyncio
import logging
import sqlite3
from datetime import datetime
from itertools import chain
from json import dumps
from random import choice

import telepot
import telepot.aio

import config


logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', level=logging.INFO)
logger = logging.getLogger(config.bot_username)
bot = telepot.aio.Bot(config.bot_token)
loop = asyncio.get_event_loop()

user_ans_db = sqlite3.connect("answers.db")
user_ans_curr = user_ans_db.cursor()

admins_list = config.load_admins()
got_user_response = list(chain.from_iterable(user_ans_curr.execute("SELECT id FROM user_answers")))
users = asyncio.Queue()
chat_semaphores = {}


def switch_welcome_message():
    current_hour = datetime.now().hour
    if current_hour in config.night_time:
        return choice(config.daytime_messages['night'])
    elif current_hour in config.morning_time:
        return choice(config.daytime_messages['morning'])
    elif current_hour in config.day_time:
        return choice(config.daytime_messages['day'])
    elif current_hour in config.evening_time:
        return choice(config.daytime_messages['evening'])


async def welcome_user(msg_id, chat_id):
    global chat_semaphores, users
    usernames = []
    while not users.empty():
        logger.debug("Starting to extract users")
        while not users.empty():
            usernames.append(await users.get())
        logger.debug("Waiting for new users to come in")
        await asyncio.sleep(config.wait_time)
    logger.debug("Welcoming user(s)")
    if len(usernames) == 1:
        await bot.sendMessage(chat_id=chat_id,
                              text=''.join([f"{switch_welcome_message()} {usernames[0]}!", choice(config.welcome_user)]),
                              reply_to_message_id=msg_id)
    elif len(usernames) > 1:
        await bot.sendMessage(chat_id=chat_id,
                              text=''.join([f"{switch_welcome_message()} {', '.join(usernames).strip()}!", choice(config.welcome_users)]))
    chat_semaphores[chat_id] = False


async def handle(msg):
    global chat_semaphores, users
    content_type, chat_type, chat_id = telepot.glance(msg)
    if chat_id not in chat_semaphores:
        chat_semaphores[chat_id] = False
    if chat_type == 'supergroup' and msg['from']['id'] in admins_list:
        if 'text' in msg:
            if msg['text'] == "/get_id":
                if 'reply_to_message' in msg:
                    await bot.sendMessage(chat_id=chat_id,
                                          text=f"User ID: {msg['reply_to_message']['from']['id']}",
                                          reply_to_message_id=msg['message_id'])
            if msg['text'] == "/rules":
                await bot.sendMessage(chat_id=chat_id,
                                      text=config.rules)
    if 'new_chat_member' in msg and chat_type == 'supergroup':
        logger.info(f"Got new chat member {msg['new_chat_member']['first_name']}")
        if 'username' in msg['new_chat_member']:
            await users.put("@" + msg['new_chat_member']['username'])
            if not chat_semaphores[chat_id]:
                loop.create_task(welcome_user(msg['message_id'], chat_id))
                chat_semaphores[chat_id] = True
                logger.debug("Started coroutine")
        elif 'last_name' in msg['new_chat_member']:
            await users.put(msg['new_chat_member']['first_name'] + " " + msg['new_chat_member']['last_name'])
            if not chat_semaphores[chat_id]:
                loop.create_task(welcome_user(msg['message_id'], chat_id))
                chat_semaphores[chat_id] = True
                logger.debug("Started coroutine")
        else:
            await users.put(msg['new_chat_member']['first_name'])
            if not chat_semaphores[chat_id]:
                loop.create_task(welcome_user(msg['message_id'], chat_id))
                chat_semaphores[chat_id] = True
                logger.debug("Started coroutine")
    elif 'reply_to_message' in msg:
        if msg['reply_to_message']['from']['username'] == config.bot_username[1:]:
            if msg['from']['id'] not in got_user_response:
                logger.info(f"Got response from user: {msg['from']['first_name']}, User ID: {msg['from']['id']}")
                user_ans_curr.execute("INSERT INTO user_answers (id, user_message) VALUES (?, ?)",
                                      (msg['from']['id'], msg['text']))
                user_ans_db.commit()
    elif chat_id in admins_list:
        if 'forward_from' in msg:
            if msg['forward_from']['id'] not in got_user_response:
                user_ans_curr.execute("INSERT INTO user_answers (id, user_message) VALUES (?, ?)",
                                      (msg['forward_from']['id'], msg['text']))
                user_ans_db.commit()
                got_user_response.append(msg['forward_from']['id'])
                await bot.sendMessage(chat_id=chat_id,
                                      text="Ответ был успешно записан в базу данных")
            else:
                await bot.sendMessage(chat_id=chat_id,
                                      text="Ответ уже есть в базе данных")
    logger.info(f"Chat: {content_type} {chat_type} {chat_id}\n"
                f"{dumps(msg, indent=4)}")


def main():
    loop.create_task(bot.message_loop(handle))

    loop.run_forever()


if __name__ == "__main__":
    main()
