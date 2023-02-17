import aiohttp, asyncio, time, datetime
from aiogram.types import Message
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from aiogram import executor

# Версия python на которой всё тестировалось: 3.8.6 64-bit

# Перед запуском необходимо установить зависимости:
# pip install aiohttp aiogram

# Автор скрипта - https://t.me/billion_er
# Если вдруг кто-то захочет задонатить, то можете задонатить вот сюда - 0x0e09a18d1ee2FA15AC811cBAe5169434781a1974 

# Запуск скрипта:
# python shardeum.py


# Тут думаю можно понять логику настройки, просто добавляем в список настройки для каждой ноды
# Параметр token это X-Api-Token из хедерсов запроса на dashboard странице ноды. Просто CTRL+SHIFT+I и смотрим любой запрос к ноде, и там он будет
NODES = [
    {"name": "node1", "host": "127.0.0.1:8080", "token": "" },
    {"name": "node2", "host": "127.0.0.1:8080", "token": "" },
    {"name": "node3", "host": "127.0.0.1:8080", "token": "" },
]


TOKEN = "" # Токен из https://t.me/BotFather
ADMIN = 123123 # ВАШ USER_ID из https://t.me/creationdatebot


# /help - Узнать все доступные комманды в телеграмм боте



information_message = """<b>Shardeum Info (State | Name (Host) | Stake Amount | Rewards | Last active)</b>:\n
{}

Total rewards: {} coins"""


help_message = """/start - стартовое сообщение
/nodes_info - информация по нодам
/start_nodes NAME NAME - включить ноды
/stop_nodes NAME NAME - отключить ноды"""


stop_nodes_message = """<b>Результат выполнения комманды <pre>/stop_nodes</pre></b>:
{}"""



loop = asyncio.get_event_loop()
storage = MemoryStorage()
bot = Bot(token=TOKEN, loop=loop, parse_mode="HTML")
dp = Dispatcher(bot, storage=storage)


# Эта функция для корректного отображения чисел с большим количеством нулей после запятой
def PriceToStr(price):

    if "-" in str(price):
        price = str(price).replace("-", '')

    if str(price).count(".") > 1:
        price = (str(price)[:-(str(price)[::-1].index(".") + 1)]).replace(".", "")

    price = float(price)

    if price == 0:
        pass
    elif price < 0.0001:
        price = str(price)[:len(str(price).split("e")[0])] + f'e{str(price).split("e")[1].replace("0", "")}'
        if "." in price:
            price = price.split('.')[0] + "." + price.split('.')[1].split("e")[0][:2] + "e" + \
                    price.split('.')[1].split("e")[1]

    elif price < 1:
        count = 0
        for i in str(price).replace(".", ""):
            if i == '0':
                count += 1
            else:
                break
        price = str(price * (10 ** count)) + f'e-{count}'
        price = price.split('.')[0] + "." + price.split('.')[1].split("e")[0][:2] + "e" + \
                price.split('.')[1].split("e")[1]

    elif price > 1:
        count = len(str(price).split(".")[0]) - 4
        if count > 0:
            price = str(price)[:4] + f"e+{count}"
        else:
            price = str(price)[:6]

    return price



async def get_node_info(node_params):
    node_url = node_params["host"]
    node_api_token = node_params["token"]
    
    headers = {"X-Api-Token": node_api_token}
    
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f"https://{node_url}/api/node/status", headers=headers, ssl=False) as response:
            if response.status == 200:
                message = await response.json()
                return {"success": True, "message": message, "node_params": node_params}
            else:
                message = await response.json()
                return {"success": False, "message": message, "node_params": node_params}



async def get_nodes_info():
    tasks = []
    
    for node_params in NODES:
        tasks.append(asyncio.create_task(get_node_info(node_params)))
    
    results = await asyncio.gather(*tasks)
    total_rewards = 0
    messages = []
    
    errors = []
    
    
    for i in results:
        if i["success"]:
            node_name = i["node_params"]["name"]
            node_host = i["node_params"]["host"]
            node_params = i["node_params"]
            node_message = i["message"]
            stake_amount = node_message["lockedStake"] + " SHM"
            state = node_message["state"]
            
            
            if state == "active":
                current_rewards = node_message["currentRewards"]
                total_rewards += float(current_rewards)
                last_active = node_message["lastActive"]
                last_active_dt = datetime.datetime.fromtimestamp(int(float(last_active)/1000)).strftime("%d.%m.%Y %H:%M:%S")
                
                message = f"✅({state.upper()}) | {node_name} ({node_host}) | Staked: {stake_amount} | Rewards: {current_rewards[0:3]} | Last active: {last_active_dt}"
                messages.append(message)
            elif state == "stopped":
                message = f"❌({state.upper()}) | {node_name} ({node_host}) | Staked: {stake_amount} |"
                messages.append(message)
                errors.append(node_name)


        else:
            message = f"❌ | {node_name} ({node_host})"
            errors.append(node_name)
    
    return {"text": information_message.format("\n\n".join(messages), PriceToStr(total_rewards)), "errors": errors}




async def stop_node_func(node_params):
    node_url = node_params["host"]
    node_api_token = node_params["token"]
    
    headers = {"X-Api-Token": node_api_token}
    
    async with aiohttp.ClientSession(trust_env=True) as session:
        node_url = node_params["host"]
        async with session.post(f"https://{node_url}/api/node/stop", headers=headers, ssl=False) as response:
            if response.status == 200:
                return {"success": True, "node_params": node_params}
            else:
                return {"success": False, "node_params": node_params}

async def start_node_func(node_params):
    node_url = node_params["host"]
    node_api_token = node_params["token"]
    
    headers = {"X-Api-Token": node_api_token}
    
    async with aiohttp.ClientSession(trust_env=True) as session:
        node_url = node_params["host"]
        async with session.post(f"https://{node_url}/api/node/start", headers=headers, ssl=False) as response:
            if response.status == 200:
                return {"success": True, "node_params": node_params}
            else:
                return {"success": False, "node_params": node_params}



async def stop_nodes(nodes_names):
    tasks = []
    
    stop_list = []
    
    for node_params in NODES:
        if node_params["name"] in nodes_names:
            stop_list.append(node_params)

    for nodes in stop_list:
        tasks.append(asyncio.create_task(stop_node_func(nodes)))
    
    results = await asyncio.gather(*tasks)
    
    messages = []
    
    
    for i in results:
        node_name = i["node_params"]["name"]
        node_host = i["node_params"]["host"]

        if i["success"]:
            messages.append(f"✅ Нода {node_name}(<pre>{node_host}</pre>) успешно отключена!")
        else:
            messages.append(f"❌ Не удалось отключить ноду {node_name}(<pre>{node_host}</pre>)!")

    return stop_nodes_message.format("\n\n".join(messages))



async def start_nodes(nodes_names):
    tasks = []
    
    start_list = []
    
    for node_params in NODES:
        if node_params["name"] in nodes_names:
            start_list.append(node_params)

    for nodes in start_list:
        tasks.append(asyncio.create_task(start_node_func(nodes)))

    results = await asyncio.gather(*tasks)
    
    messages = []
    
    
    for i in results:
        node_name = i["node_params"]["name"]
        node_host = i["node_params"]["host"]

        if i["success"]:
            messages.append(f"✅ Нода {node_name}(<pre>{node_host}</pre>) успешно запущена!")
        else:
            messages.append(f"❌ Не удалось запустить ноду {node_name}(<pre>{node_host}</pre>)!")


    return stop_nodes_message.format("\n\n".join(messages))



async def restart_nodes():
    while True:
        actual_info = await get_nodes_info()
        errors_names = actual_info["errors"]
        errors_count = len(errors_names)
        
        if errors_count > 0:
            await bot.send_message(ADMIN, f"Обнаружено {errors_count} отключенных нод({', '.join(errors_names)}), перезапускаю их!")
            text = await start_nodes(actual_info["errors"])
            await bot.send_message(ADMIN, text)

        await asyncio.sleep(5)


@dp.message_handler(commands=['start'])
async def welcome(message: Message):
    if message.from_user.id == ADMIN:
        await message.reply("Добро пожаловать в мега-удобную хуйню для менеджмента шардеума.")

@dp.message_handler(commands=['help'])
async def welcome(message: Message):
    if message.from_user.id == ADMIN:
        await message.reply(help_message)


@dp.message_handler(commands=['nodes_info'])
async def nodes_info(message: Message):
    if message.from_user.id == ADMIN:
        nodes_info = await get_nodes_info()
        await bot.send_message(message.from_user.id, nodes_info["text"])


@dp.message_handler(commands=['stop_nodes'])
async def stop_node(message: Message):
    if message.from_user.id == ADMIN:
        nodes_names = message.text.split("/stop_nodes ")[1].split(" ")
        result = await stop_nodes(nodes_names)
        await bot.send_message(message.from_user.id, result)


@dp.message_handler(commands=['start_nodes'])
async def start_node(message: Message):
    if message.from_user.id == ADMIN:
        nodes_names = message.text.split("/start_nodes ")[1].split(" ")
        result = await start_nodes(nodes_names)
        await bot.send_message(message.from_user.id, result)


loop = asyncio.get_event_loop()
# это херня которая чекает доступность всех ваших нод, и в случае чего реанимирует их
loop.create_task(restart_nodes())
executor.start_polling(dp, skip_updates=True)