import telebot
import wikipedia
import re
from telebot import types
from warnings import filterwarnings
from gtts import gTTS
import os
import tempfile
import hashlib
import requests
from urllib.parse import urljoin
import time
import threading
from datetime import datetime, timedelta

filterwarnings("ignore", category=UserWarning, module='wikipedia')

bot = telebot.TeleBot('7967328415:AAHOjXfv8Oa8ChCTRTuJJ-gBUASpV5EfZHA')

current_language = 'en'
sound_mode = {}  # Dictionary for tracking users in sound mode
search_results = {}
reminders = {}  # Dictionary to store user reminders
stopwatches = {}  # Dictionary to track stopwatches
alarms = {}  # Dictionary to track alarms

# Add new language texts for the new features
language_texts = {
    'en': {
        # Previous texts...
        'reminder_set': "Reminder set for {time}. I'll notify you with: {text}",
        'reminder_list': "Your reminders:\n{reminders_list}",
        'no_reminders': "You have no active reminders.",
        'reminder_notification': "🔔 Reminder: {text}",
        'reminder_cancelled': "Reminder cancelled.",
        'invalid_reminder_time': "Invalid time format. Please use HH:MM or HH:MM:SS.",
        'stopwatch_started': "Stopwatch started! Use /stopwatch to check elapsed time.",
        'stopwatch_stopped': "Stopwatch stopped. Elapsed time: {time}",
        'stopwatch_reset': "Stopwatch reset.",
        'stopwatch_current': "Elapsed time: {time}",
        'alarm_set': "Alarm set for {time}. I'll notify you then.",
        'alarm_list': "Your alarms:\n{alarms_list}",
        'no_alarms': "You have no active alarms.",
        'alarm_notification': "⏰ Alarm! Wake up!",
        'alarm_cancelled': "Alarm cancelled.",
        'invalid_alarm_time': "Invalid time format. Please use HH:MM.",
        'time_input_prompt': "Please enter the time (HH:MM or HH:MM:SS for reminders, HH:MM for alarms):",
        'reminder_text_prompt': "Please enter the reminder text:",
        'reminder_help': "To set a reminder: /reminder HH:MM Your reminder text\nTo list reminders: /reminders\nTo cancel a reminder: /cancelreminder ID",
        'stopwatch_help': "To start stopwatch: /startstopwatch\nTo check time: /stopwatch\nTo stop and reset: /stopstopwatch",
        'alarm_help': "To set an alarm: /alarm HH:MM\nTo list alarms: /alarms\nTo cancel an alarm: /cancelalarm ID"
    },
    'ru': {
        # Previous texts...
        'reminder_set': "Напоминание установлено на {time}. Я напомню вам: {text}",
        'reminder_list': "Ваши напоминания:\n{reminders_list}",
        'no_reminders': "У вас нет активных напоминаний.",
        'reminder_notification': "🔔 Напоминание: {text}",
        'reminder_cancelled': "Напоминание отменено.",
        'invalid_reminder_time': "Неверный формат времени. Используйте ЧЧ:ММ или ЧЧ:ММ:СС.",
        'stopwatch_started': "Секундомер запущен! Используйте /stopwatch для проверки времени.",
        'stopwatch_stopped': "Секундомер остановлен. Прошедшее время: {time}",
        'stopwatch_reset': "Секундомер сброшен.",
        'stopwatch_current': "Прошедшее время: {time}",
        'alarm_set': "Будильник установлен на {time}. Я разбужу вас тогда.",
        'alarm_list': "Ваши будильники:\n{alarms_list}",
        'no_alarms': "У вас нет активных будильников.",
        'alarm_notification': "⏰ Будильник! Просыпайтесь!",
        'alarm_cancelled': "Будильник отменён.",
        'invalid_alarm_time': "Неверный формат времени. Используйте ЧЧ:ММ.",
        'time_input_prompt': "Пожалуйста, введите время (ЧЧ:ММ или ЧЧ:ММ:СС для напоминаний, ЧЧ:ММ для будильников):",
        'reminder_text_prompt': "Пожалуйста, введите текст напоминания:",
        'reminder_help': "Чтобы установить напоминание: /reminder ЧЧ:ММ Ваш текст\nЧтобы посмотреть напоминания: /reminders\nЧтобы отменить: /cancelreminder ID",
        'stopwatch_help': "Чтобы запустить секундомер: /startstopwatch\nПроверить время: /stopwatch\nОстановить и сбросить: /stopstopwatch",
        'alarm_help': "Чтобы установить будильник: /alarm ЧЧ:ММ\nПосмотреть будильники: /alarms\nОтменить будильник: /cancelalarm ID"
    },
    # Add translations for other languages similarly...
}


# Helper function to format time
def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# Reminder management
def check_reminders():
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")

        # Check reminders
        for user_id, user_reminders in list(reminders.items()):
            for reminder_id, reminder in list(user_reminders.items()):
                if reminder['time'] <= current_time:
                    try:
                        bot.send_message(user_id, language_texts[reminder['language']]['reminder_notification'].format(
                            text=reminder['text']))
                        del reminders[user_id][reminder_id]
                    except Exception as e:
                        print(f"Error sending reminder: {e}")

        # Check alarms
        current_time_hm = now.strftime("%H:%M")
        for user_id, user_alarms in list(alarms.items()):
            for alarm_id, alarm in list(user_alarms.items()):
                if alarm['time'] == current_time_hm:
                    try:
                        bot.send_message(user_id, language_texts[alarm['language']]['alarm_notification'])
                        # Remove one-time alarms
                        if alarm.get('repeating', False):
                            # For repeating alarms, set the next occurrence
                            alarm_time = datetime.strptime(alarm['time'], "%H:%M")
                            next_time = (now + timedelta(days=1)).strftime("%H:%M")
                            alarms[user_id][alarm_id]['time'] = next_time
                        else:
                            del alarms[user_id][alarm_id]
                    except Exception as e:
                        print(f"Error sending alarm: {e}")

        time.sleep(1)


# Start the reminder/alarm checking thread
reminder_thread = threading.Thread(target=check_reminders)
reminder_thread.daemon = True
reminder_thread.start()


# Add new command handlers
@bot.message_handler(commands=["reminder", "remindme"])
def set_reminder(message):
    user_id = message.from_user.id
    lang = current_language

    try:
        # Parse command arguments
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.send_message(user_id, language_texts[lang]['time_input_prompt'])
            bot.register_next_step_handler(message, process_reminder_time)
            return

        time_str = parts[1]
        reminder_text = parts[2]

        # Validate time format
        try:
            datetime.strptime(time_str, "%H:%M:%S")
            time_format = "%H:%M:%S"
        except ValueError:
            try:
                datetime.strptime(time_str, "%H:%M")
                time_format = "%H:%M"
            except ValueError:
                bot.send_message(user_id, language_texts[lang]['invalid_reminder_time'])
                return

        # Store reminder
        if user_id not in reminders:
            reminders[user_id] = {}

        reminder_id = str(int(time.time()))
        reminders[user_id][reminder_id] = {
            'time': time_str,
            'text': reminder_text,
            'language': lang
        }

        bot.send_message(user_id, language_texts[lang]['reminder_set'].format(
            time=time_str, text=reminder_text))

    except Exception as e:
        print(f"Error setting reminder: {e}")
        bot.send_message(user_id, language_texts[lang]['general_error'])


def process_reminder_time(message):
    user_id = message.from_user.id
    lang = current_language
    time_str = message.text.strip()

    try:
        # Validate time format
        try:
            datetime.strptime(time_str, "%H:%M:%S")
            time_format = "%H:%M:%S"
        except ValueError:
            try:
                datetime.strptime(time_str, "%H:%M")
                time_format = "%H:%M"
            except ValueError:
                bot.send_message(user_id, language_texts[lang]['invalid_reminder_time'])
                return

        bot.send_message(user_id, language_texts[lang]['reminder_text_prompt'])
        bot.register_next_step_handler(message, process_reminder_text, time_str)

    except Exception as e:
        print(f"Error processing reminder time: {e}")
        bot.send_message(user_id, language_texts[lang]['general_error'])


def process_reminder_text(message, time_str):
    user_id = message.from_user.id
    lang = current_language
    reminder_text = message.text.strip()

    try:
        # Store reminder
        if user_id not in reminders:
            reminders[user_id] = {}

        reminder_id = str(int(time.time()))
        reminders[user_id][reminder_id] = {
            'time': time_str,
            'text': reminder_text,
            'language': lang
        }

        bot.send_message(user_id, language_texts[lang]['reminder_set'].format(
            time=time_str, text=reminder_text))

    except Exception as e:
        print(f"Error processing reminder text: {e}")
        bot.send_message(user_id, language_texts[lang]['general_error'])


@bot.message_handler(commands=["reminders"])
def list_reminders(message):
    user_id = message.from_user.id
    lang = current_language

    if user_id not in reminders or not reminders[user_id]:
        bot.send_message(user_id, language_texts[lang]['no_reminders'])
        return

    reminders_list = []
    for reminder_id, reminder in reminders[user_id].items():
        reminders_list.append(f"{reminder_id}: {reminder['time']} - {reminder['text']}")

    bot.send_message(user_id, language_texts[lang]['reminder_list'].format(
        reminders_list="\n".join(reminders_list)))


@bot.message_handler(commands=["cancelreminder"])
def cancel_reminder(message):
    user_id = message.from_user.id
    lang = current_language

    try:
        reminder_id = message.text.split(maxsplit=1)[1].strip()

        if user_id in reminders and reminder_id in reminders[user_id]:
            del reminders[user_id][reminder_id]
            bot.send_message(user_id, language_texts[lang]['reminder_cancelled'])
        else:
            bot.send_message(user_id, language_texts[lang]['no_reminders'])

    except Exception as e:
        print(f"Error canceling reminder: {e}")
        bot.send_message(user_id, language_texts[lang]['general_error'])


# Stopwatch commands
@bot.message_handler(commands=["startstopwatch"])
def start_stopwatch(message):
    user_id = message.from_user.id
    lang = current_language

    if user_id not in stopwatches:
        stopwatches[user_id] = {
            'start_time': time.time(),
            'running': True
        }
    else:
        if not stopwatches[user_id]['running']:
            stopwatches[user_id]['start_time'] = time.time() - (
                stopwatches[user_id].get('elapsed', 0))
            stopwatches[user_id]['running'] = True

    bot.send_message(user_id, language_texts[lang]['stopwatch_started'])


@bot.message_handler(commands=["stopwatch"])
def check_stopwatch(message):
    user_id = message.from_user.id
    lang = current_language

    if user_id in stopwatches and stopwatches[user_id]['running']:
        elapsed = time.time() - stopwatches[user_id]['start_time']
        bot.send_message(user_id, language_texts[lang]['stopwatch_current'].format(
            time=format_time(int(elapsed))))
    else:
        bot.send_message(user_id, language_texts[lang]['stopwatch_current'].format(
            time=format_time(0)))


@bot.message_handler(commands=["stopstopwatch"])
def stop_stopwatch(message):
    user_id = message.from_user.id
    lang = current_language

    if user_id in stopwatches and stopwatches[user_id]['running']:
        elapsed = time.time() - stopwatches[user_id]['start_time']
        stopwatches[user_id]['elapsed'] = elapsed
        stopwatches[user_id]['running'] = False
        bot.send_message(user_id, language_texts[lang]['stopwatch_stopped'].format(
            time=format_time(int(elapsed))))
    else:
        bot.send_message(user_id, language_texts[lang]['stopwatch_current'].format(
            time=format_time(0)))


@bot.message_handler(commands=["resetstopwatch"])
def reset_stopwatch(message):
    user_id = message.from_user.id
    lang = current_language

    if user_id in stopwatches:
        stopwatches[user_id] = {
            'start_time': time.time(),
            'running': True,
            'elapsed': 0
        }
    else:
        stopwatches[user_id] = {
            'start_time': time.time(),
            'running': True
        }

    bot.send_message(user_id, language_texts[lang]['stopwatch_reset'])


# Alarm commands
@bot.message_handler(commands=["alarm"])
def set_alarm(message):
    user_id = message.from_user.id
    lang = current_language

    try:
        time_str = message.text.split(maxsplit=1)[1].strip()

        # Validate time format
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            bot.send_message(user_id, language_texts[lang]['invalid_alarm_time'])
            return

        # Store alarm
        if user_id not in alarms:
            alarms[user_id] = {}

        alarm_id = str(int(time.time()))
        alarms[user_id][alarm_id] = {
            'time': time_str,
            'language': lang,
            'repeating': False  # Change to True for repeating alarms
        }

        bot.send_message(user_id, language_texts[lang]['alarm_set'].format(
            time=time_str))

    except Exception as e:
        print(f"Error setting alarm: {e}")
        bot.send_message(user_id, language_texts[lang]['general_error'])


@bot.message_handler(commands=["alarms"])
def list_alarms(message):
    user_id = message.from_user.id
    lang = current_language

    if user_id not in alarms or not alarms[user_id]:
        bot.send_message(user_id, language_texts[lang]['no_alarms'])
        return

    alarms_list = []
    for alarm_id, alarm in alarms[user_id].items():
        repeat_status = " (repeating)" if alarm.get('repeating', False) else ""
        alarms_list.append(f"{alarm_id}: {alarm['time']}{repeat_status}")

    bot.send_message(user_id, language_texts[lang]['alarm_list'].format(
        alarms_list="\n".join(alarms_list)))


@bot.message_handler(commands=["cancelalarm"])
def cancel_alarm(message):
    user_id = message.from_user.id
    lang = current_language

    try:
        alarm_id = message.text.split(maxsplit=1)[1].strip()

        if user_id in alarms and alarm_id in alarms[user_id]:
            del alarms[user_id][alarm_id]
            bot.send_message(user_id, language_texts[lang]['alarm_cancelled'])
        else:
            bot.send_message(user_id, language_texts[lang]['no_alarms'])

    except Exception as e:
        print(f"Error canceling alarm: {e}")
        bot.send_message(user_id, language_texts[lang]['general_error'])


# Help commands for new features
@bot.message_handler(commands=["reminderhelp"])
def reminder_help(message):
    user_id = message.from_user.id
    lang = current_language
    bot.send_message(user_id, language_texts[lang]['reminder_help'])


@bot.message_handler(commands=["stopwatchhelp"])
def stopwatch_help(message):
    user_id = message.from_user.id
    lang = current_language
    bot.send_message(user_id, language_texts[lang]['stopwatch_help'])


@bot.message_handler(commands=["alarmhelp"])
def alarm_help(message):
    user_id = message.from_user.id
    lang = current_language
    bot.send_message(user_id, language_texts[lang]['alarm_help'])


# ... (keep all your existing code)

if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)