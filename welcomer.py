# -*- coding: utf-8 -*-

import asyncio
import logging
import sqlite3
from datetime import datetime
from itertools import chain
from json import dumps
from random import choice
import time

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
got_user_response = list(chain.from_iterable(user_ans_curr.execute("SELECT user_id FROM user_answers")))
messages_from_users = list(chain.from_iterable(user_ans_curr.execute("SELECT user_message FROM user_answers")))
curr_users, prev_users, time_users = {}, {}, {}
prev_bot_messages, chat_messages_count = {}, {}
chat_semaphores = {}

def username_from_msg(msg, flag=0):
    if flag == 0:
        if 'username' in msg['from']:
            return f"@{msg['from']['username']}"
        elif 'last_name' in msg['from']:
            return f"{msg['from']['first_name']} {msg['from']['last_name']}"
        else:
            return f"{msg['from']['first_name']}"
    elif flag == 1:
        if 'username' in msg['new_chat_member']:
            return f"@{msg['new_chat_member']['username']}"
        elif 'last_name' in msg['new_chat_member']:
            return f"{msg['new_chat_member']['first_name']} {msg['new_chat_member']['last_name']}"
        else:
            return f"{msg['new_chat_member']['first_name']}"
    elif flag == 2:
        if 'username' in msg['forward_from']:
            return f"@{msg['forward_from']['username']}"
        elif 'last_name' in msg['forward_from']:
            return f"{msg['forward_from']['first_name']} {msg['forward_from']['last_name']}"
        else:
            return f"{msg['forward_from']['first_name']}"
    elif flag == 3:
        if 'username' in msg['left_chat_member']:
            return f"@{msg['left_chat_member']['username']}"
        elif 'last_name' in msg['left_chat_member']:
            return f"{msg['left_chat_member']['first_name']} {msg['left_chat_member']['last_name']}"
        else:
            return f"{msg['left_chat_member']['first_name']}"

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
    global chat_semaphores, curr_users, prev_users, time_users, prev_bot_messages, chat_messages_count
    logger.debug("Waiting for new users to come in")
    await asyncio.sleep(config.wait_time)
    
    if len(curr_users[chat_id]) > 0:
        if chat_id in prev_users:
            update = len(prev_users[chat_id]) > 0
            for user in prev_users[chat_id]:
                if user not in curr_users[chat_id]:
                    update = False
                    break
            if update and (config.min_msg_count < 0 or chat_messages_count[chat_id] < config.min_msg_count):
                await bot.deleteMessage(prev_bot_messages[chat_id])
            elif config.clear_prev_users:
                for user in prev_users[chat_id]:
                    if user in curr_users[chat_id]: curr_users[chat_id].remove(user)
        prev_users[chat_id] = curr_users[chat_id][::]        
        logger.debug("Welcoming user(s)")
        if len(curr_users[chat_id]) == 1:
            prev_bot_messages[chat_id] = telepot.message_identifier(await bot.sendMessage(chat_id=chat_id,
                                  text=' '.join([f"{switch_welcome_message()} {curr_users[chat_id][0]}!", choice(config.welcome_user)]),
                                  reply_to_message_id=msg_id))
        elif len(curr_users[chat_id]) > 1:
            prev_bot_messages[chat_id] = telepot.message_identifier(await bot.sendMessage(chat_id=chat_id,
                                  text=' '.join([f"{switch_welcome_message()} {', '.join(curr_users[chat_id]).strip()}!", choice(config.welcome_users)])))
    chat_semaphores[chat_id] = False
    chat_messages_count[chat_id] = 0

async def handle(msg):
    global chat_semaphores, curr_users, time_users, chat_messages_count
    content_type, chat_type, chat_id = telepot.glance(msg)    
    if chat_id not in curr_users: curr_users[chat_id] = []
    if chat_id not in time_users: time_users[chat_id] = {}
    if chat_id not in chat_messages_count: chat_messages_count[chat_id] = 0
    copy_curr_users = curr_users[chat_id][::]
    curr_time = time.time()
    for user in copy_curr_users:
        if user in time_users[chat_id] and time_users[chat_id][user] + config.wait_response_time <= curr_time:
            if user in curr_users[chat_id]: curr_users[chat_id].remove(user)
    if chat_id not in chat_semaphores:
        chat_semaphores[chat_id] = False
    chat_messages_count[chat_id]+=1    
    if msg['from']['id'] in admins_list:
        if 'text' in msg:
            if 'reply_to_message' in msg:
                if msg['text'] == "Ава спроси" or msg['text'] == "Ава, спроси":
                    await bot.sendMessage(chat_id=chat_id,
                        text=' '.join([choice(config.welcome_user)]),
                        reply_to_message_id=msg['reply_to_message']['message_id'])
                if msg['text'] == "Ава расскажи" or msg['text'] == "Ава, расскажи":
                    logger.info(f"извлекаем из базы всякие теги для {msg['reply_to_message']['from']['id']}")       
                    string_ = "select distinct Tags.name from user_answers UA inner join tags_user TU on (TU.user_id = UA.user_id) inner join tags Tags on (TU.tags_id = Tags.id) where UA.user_id = " + str(msg['reply_to_message']['from']['id'])
                    #logger.info(string_)
                    #user_ans_curr.execute(string_)
                    tags = list(chain.from_iterable(user_ans_curr.execute(string_)))
                    #logger.info(user_ans_curr.fetchone()) 
                    await bot.sendMessage(chat_id=chat_id,
                        text=msg['reply_to_message']['from']['first_name'] + ': ' + ' '.join(str(value) for value in tags),
                        reply_to_message_id=msg['message_id'])
                        #print(cursor.fetchone()) 
                    user_ans_db.commit()
    if msg['from']['id'] in admins_list:
        if 'reply_to_message' in msg:
            if 'text' in msg:
                if msg['text'] == "/kick" or msg['text'] == "/ban":
                    await bot.kickChatMember(chat_id=chat_id,
                        user_id=msg['reply_to_message']['from']['id'])
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
    if 'new_chat_member' in msg and msg['new_chat_member']['id'] == config.Sergey:
        await bot.sendMessage(chat_id=chat_id,
            text=f"get ur ass outta here",
            reply_to_message_id=msg['message_id'])
    if 'new_chat_member' in msg and chat_type == 'supergroup':
        timestamp = int(time.time())
        await bot.restrictChatMember(chat_id=chat_id,
            user_id=msg['new_chat_member']['id'],
            until_date=timestamp, 
            can_send_messages=True, 
            can_send_media_messages=False, 
            can_send_other_messages=False, 
            can_add_web_page_previews=False)
        logger.info(f"Got new chat member {msg['new_chat_member']['first_name']}")
        user = username_from_msg(msg, flag=1)
        if user not in curr_users[chat_id] and (not config.check_response or msg['new_chat_member']['id'] not in got_user_response):
            curr_users[chat_id].append(user)
            if not chat_semaphores[chat_id]:
                loop.create_task(welcome_user(msg['message_id'], chat_id))
                chat_semaphores[chat_id] = True
                logger.debug("Started coroutine")
    if 'left_chat_member' in msg and chat_type == 'supergroup':
        logger.info(f"Got left chat member {msg['left_chat_member']['first_name']}")
        user = username_from_msg(msg, flag=3)
        if user in curr_users[chat_id]: curr_users[chat_id].remove(user)
    if 'reply_to_message' in msg:
        if msg['reply_to_message']['from']['username'] == config.bot_username[1:]:
            if msg['from']['id'] not in got_user_response:
                timestamp1 = int(time.time())
                await bot.restrictChatMember(chat_id=chat_id,
                    user_id=msg['from']['id'],
                    until_date=timestamp1, 
                    can_send_messages=True, 
                    can_send_media_messages=True, 
                    can_send_other_messages=True, 
                    can_add_web_page_previews=True)
                logger.info(f"Got response from user: {msg['from']['first_name']}, User ID: {msg['from']['id']}")
                user = username_from_msg(msg)
                user_ans_curr.execute("INSERT INTO user_answers (user_id, message_id, username, user_message) VALUES (?, ?, ?, ?)",
                                      (msg['from']['id'], msg['message_id'], user, msg['text']))
                user_ans_db.commit()
                got_user_response.append(msg['from']['id'])
                if user in curr_users[chat_id]: curr_users[chat_id].remove(user)
    elif chat_id in admins_list:
        if 'forward_from' in msg:
            if msg['text'] not in messages_from_users:
                user = username_from_msg(msg, flag=2)
                user_ans_curr.execute("INSERT INTO user_answers (user_id, message_id, username, user_message) VALUES (?, ?, ?, ?)",
                                      (msg['forward_from']['id'], 0, user, msg['text']))
                user_ans_db.commit()
                timestamp2 = int(time.time())
                await bot.restrictChatMember(chat_id=config.myChat,
                    user_id=msg['forward_from']['id'],
                    until_date=timestamp2, 
                    can_send_messages=True, 
                    can_send_media_messages=True, 
                    can_send_other_messages=True, 
                    can_add_web_page_previews=True)
                await bot.sendMessage(chat_id=chat_id,
                                      text="Ответ был успешно записан в базу данных")
                messages_from_users.append(msg['text'])
                if user in curr_users[chat_id]: curr_users[chat_id].remove(user)
            else:
                await bot.sendMessage(chat_id=chat_id,
                                      text="Ответ уже есть в базе данных")
    logger.info(f"Chat: {content_type} {chat_type} {chat_id}\n"
                f"{dumps(msg, indent=4, ensure_ascii=False)}")

def main():
    loop.create_task(bot.message_loop(handle))

    loop.run_forever()

if __name__ == "__main__":
    main()
