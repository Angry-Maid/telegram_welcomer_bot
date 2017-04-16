# -*- coding: utf-8 -*-

import asyncio
import logging
import sqlite3
from datetime import datetime
from itertools import chain
from pprint import pprint

import telepot
import telepot.aio

import config

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(config.bot_username)
bot = telepot.aio.Bot(config.bot_token)
loop = asyncio.get_event_loop()

user_ans_db = sqlite3.connect("answers.db")
user_ans_curr = user_ans_db.cursor()

admins_list = config.load_admins()
got_user_response = list(chain.from_iterable(user_ans_curr.execute("SELECT id FROM user_answers")))
users = asyncio.Queue()

"""
{<Task pending coro=<handle() running at main.py:75>>, 
<Task pending coro=<Bot.message_loop() running at \bots\lib\site-packages\telepot\aio\__init__.py:580> 
wait_for=<Future pending cb=[<TaskWakeupMethWrapper object at 0x02586770>()]>>,
<Task pending coro=<welcome_user() running at main.py:42>>}
"""


def switch_welcome_message():
    current_hour = datetime.now().hour
    print(datetime().now().hour)
    if 0 >= current_hour <= 6:
        return "Доброй ночи, неспящий(ие)"
    elif 6 > current_hour <= 10:
        return "Доброго утра,"
    elif 10 > current_hour <= 17:
        return "Доброго дня,"
    elif 17 > current_hour <= 23:
        return "Доброго вечера,"


async def welcome_user(msg_id, chat_id):
    global users
    usernames = []
    while not users.empty():
        usernames.append(await users.get())
        await asyncio.sleep(20)
    if len(usernames) == 1:
        await bot.sendMessage(chat_id=chat_id,
                              text=f"{switch_welcome_message()} {usernames[0]}! "
                                   f"Расскажи немного о себе в реплае на это сообщение! "
                                   f"Что умеете в сфере I.T.? Чего ждете от чата?",
                              reply_to_message_id=msg_id)
    elif len(usernames) > 1:
        welcome_users = ', '.join(usernames).strip()
        await bot.sendMessage(chat_id=chat_id,
                              text=f"{switch_welcome_message()} {welcome_users}! "
                                   f"Расскажите немного о себе в реплае на это сообщение! "
                                   f"Что умеете в сфере I.T.? Чего ждёте от чата?")


async def handle(msg):
    global users
    content_type, chat_type, chat_id = telepot.glance(msg)
    if chat_type == 'supergroup' and msg['from']['id'] in admins_list:
        if 'reply_to_message' in msg:
            await bot.sendMessage(chat_id=chat_id,
                                  text=f"User ID: {msg['reply_to_message']['from']['id']}",
                                  reply_to_message_id=msg['message_id'])
    if 'new_chat_member' in msg and chat_type == 'supergroup':
        print(f"Got new chat member {msg['new_chat_member']['first_name']}")
        if 'username' in msg['new_chat_member']:
            await users.put("@" + msg['new_chat_member']['username'])

            # TODO: search for a way to track down running coroutine
            # Example:
            # if welcome_user in asyncio.Task.all_tasks():
            #     pass
            # else:
            #     loop.create_task(welcome_user(*args))

            loop.create_task(welcome_user(msg['message_id'], chat_id))
            print(asyncio.Task.all_tasks())
        elif 'last_name' in msg['new_chat_member']:
            await users.put(msg['new_chat_member']['first_name'] + " " + msg['new_chat_member']['last_name'])
            loop.create_task(welcome_user(msg['message_id'], chat_id))
            print(asyncio.Task.all_tasks())
        else:
            await users.put(msg['new_chat_member']['first_name'])
            loop.create_task(welcome_user(msg['message_id'], chat_id))
            print(asyncio.Task.all_tasks())
    elif 'reply_to_message' in msg:
        if msg['reply_to_message']['from']['username'] == config.bot_username[1:]:
            if msg['from']['id'] not in got_user_response:
                print(f"Got response from user: {msg['from']['first_name']}, User ID: {msg['from']['id']}")
                user_ans_curr.execute("INSERT INTO user_answers (id, user_message) VALUES (?, ?)",
                                      (msg['from']['id'], msg['text']))
                user_ans_db.commit()
    elif chat_id in admins_list:
        if 'forward_from' in msg:
            if msg['forward_from']['id'] not in got_user_response:
                user_ans_curr.execute("INSERT INTO user_answers (id, user_message) VALUES (?, ?)",
                                      (msg['forward_from']['id'], msg['forward_from']['text']))
                user_ans_db.commit()
                got_user_response.append(msg['forward_from']['id'])
                await bot.sendMessage(chat_id=chat_id,
                                      text="Ответ был успешно записан в базу данных")
            else:
                await bot.sendMessage(chat_id=chat_id,
                                      text="Ответ уже есть в базе данных")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
          f"Chat: {content_type} {chat_type} {chat_id}")
    pprint(msg)


def main():
    loop.create_task(bot.message_loop(handle))

    loop.run_forever()


if __name__ == "__main__":
    main()
