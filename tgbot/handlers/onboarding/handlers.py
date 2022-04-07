import datetime

from django.utils import timezone
from django.db.models import Max
from django.db import connection
from telegram import ParseMode, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, CommandHandler, ConversationHandler, MessageHandler, Filters

from tgbot.handlers.onboarding import static_text
from tgbot.handlers.utils.info import extract_user_data_from_update
from tgbot.models import User
from tgbot.models import StaticText
from tgbot.models import Category
from tgbot.handlers.onboarding.keyboards import make_keyboard_for_start_command


def get_dict_of_categories() -> dict:
    lvl = Category.objects.aggregate(Max('level'))['level__max']
    if lvl:
        max_category_lvl = lvl + 1
    else:
        max_category_lvl = 1
    dict_of_categories = {}
    for i in range(max_category_lvl):
        categories = Category.objects.all().filter(level=i)
        for category in categories:
            sub_categories = Category.objects.all().filter(level=i + 1).filter(above_category=category.name).all()
            if sub_categories:
                for el in sub_categories:
                    dict_of_categories[category.name] = {sub_cat.name: {} for sub_cat in sub_categories}
    return dict_of_categories


def command_start(update: Update, context: CallbackContext) -> str:
    print('starting')
    context.user_data['level'] = 0
    list_for_buttons = []
    lst = list(get_dict_of_categories().keys())
    for i in range(0, len(lst), 2):
        if i + 1 != len(lst):
            list_for_buttons.append([lst[i], lst[i + 1]])
        else:
            list_for_buttons.append([lst[i]])

    keyboard = ReplyKeyboardMarkup(list_for_buttons, resize_keyboard=True)
    text = StaticText.objects.all().filter(key_word='choice_of_category')
    if text:
        update.message.reply_text(
            text[0].text,
            reply_markup=keyboard,
        )
    else:
        print('NO TEXT')
        update.message.reply_text(
            'Категории',
            reply_markup=keyboard,
        )
    if update.message.text in get_dict_of_categories():
        return update.message.text
    else:
        print('returned')
        return 'Категории'


def category(update: Update, context: CallbackContext) -> str:
    user = update.message.from_user


def subcategory(update: Update, context: CallbackContext) -> str:
    print('subcat')
    user = update.message.from_user
    context.user_data['level'] += 1
    if update.message.text == 'Назад':
        command_start(update, context)
        return 'Категории'
    context.user_data['category'] = update.message.text

    list_of_cats = [el.name for el in Category.objects.all().filter(above_category=context.user_data['category'])]
    list_of_cats.append('Назад')
    list_for_buttons = []
    for i in range(0, len(list_of_cats), 2):
        if i + 1 != len(list_of_cats):
            list_for_buttons.append([list_of_cats[i], list_of_cats[i + 1]])
        else:
            list_for_buttons.append([list_of_cats[i]])

    keyboard = ReplyKeyboardMarkup(list_for_buttons, resize_keyboard=True)
    text = Category.objects.get(name=context.user_data['category']).text_for_chat
    update.message.reply_text(
        text,
        reply_markup=keyboard,
    )
    if update.message.text in [el.name for el in Category.objects.all()]:
        return 'Подкатегории'


def subsubcategory(update: Update, context: CallbackContext) -> str:
    print('subsubcat')
    if update.message.text == 'Назад':
        print('АХАХХАХАХАХА')
        subcategory(update, context)
        return 'Подкатегории'
    context.user_data['level'] += 1
    context.user_data['subcategory'] = update.message.text
    list_of_cats = Category.objects.all().filter(above_category=context.user_data['subcategory'])
    keyboard = ReplyKeyboardMarkup([['Пустая кнопка', 'Назад']], resize_keyboard=True)
    text = Category.objects.get(name=update.message.text).text_for_chat
    update.message.reply_text(
        text,
        reply_markup=keyboard,
    )
    if update.message.text in Category.objects.all():
        return update.message.text


def cancel(update: Update, context: CallbackContext) -> str:
    user = update.message.from_user
    lvl = context.user_data['level']
    dict_of_levels = {1: command_start, 2: subcategory}
    dict_of_names = {1: 'Категории', 2: 'Подкатегории'}
    if lvl != 0:
        context.user_data['level'] = lvl - 2
        dict_of_levels[lvl](update, context)
        return dict_of_names[lvl]


def secret_level(update: Update, context: CallbackContext) -> None:
    # callback_data: SECRET_LEVEL_BUTTON variable from manage_data.py
    """ Pressed 'secret_level_button_text' after /start command"""
    user_id = extract_user_data_from_update(update)['user_id']
    text = static_text.unlock_secret_room.format(
        user_count=User.objects.count(),
        active_24=User.objects.filter(updated_at__gte=timezone.now() - datetime.timedelta(hours=24)).count()
    )

    context.bot.edit_message_text(
        text=text,
        chat_id=user_id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )


def get_conv_handler():
    all_tables = connection.introspection.table_names()
    if 'tgbot_category' in all_tables:
        list_of_cats = Category.objects.all()
        all_tables = connection.introspection.table_names()
        conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', command_start)],
                states={
                    'Категории': [MessageHandler(Filters.regex(f"^({'|'.join(get_dict_of_categories())}|Назад)$"), subcategory)],
                    'Подкатегории': [MessageHandler(Filters.regex(f"^({'|'.join([el.name for el in list_of_cats])}|Назад)$"), subsubcategory)],
                },
                fallbacks=[CommandHandler('back', cancel)],
            )
        return conv_handler
    else:
        return ConversationHandler(entry_points=[CommandHandler('start', command_start)],
                                   states={'main_menu': [MessageHandler(Filters.text == '', category)]},
                                   fallbacks=[CommandHandler('back', cancel)])
