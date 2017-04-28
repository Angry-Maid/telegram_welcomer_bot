# telegram_welcomer_bot

This bot will welcome anyone who will join supergroup and will store answers from joined user if needed.

How to install and run bot:

> Make sure that you use Python **3.6** or later

Do `git clone` or download zip and unpack it, then open console and do:

`python -m pip install -r requirements.txt`

Create `admins.cfg` file and add ID's of admins in this file, each admin id in new line.

After that you need to create database file named `answers.db` via sqlite3(in folder in which you unpacked/cloned repository):

```sql lite
>sqlite3
sqlite3>.open --new answers.db
sqlite3>CREATE TABLE user_answers (id int, message_id int, username text, user_message text);
```

And then you need to write in your bot token (you can get it from **@botfather**) and your bot username. Finally you can run your bot via `python welcome.py`



- [ ] TODO: Add webhook support