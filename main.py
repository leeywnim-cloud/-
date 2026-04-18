import os
import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import time
import datetime
from flask import Flask
from threading import Thread

# ===== 서버 유지 =====
app = Flask('')

@app.route('/')
def home():
    return "alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# ===== 설정 =====
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "data.json"
cooldowns = {}

# ===== 데이터 =====
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_user(data, uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {
            "money": 1000,
            "xp": 0,
            "level": 1,
            "enhance": 0
        }
    return data[uid]

def cd(uid, sec):
    now = time.time()
    if uid in cooldowns and now - cooldowns[uid] < sec:
        return False
    cooldowns[uid] = now
    return True

# ===== 봇 시작 =====
@bot.event
async def on_ready():
    await tree.sync()
    print("봇 ON")

# ===== 경험치 =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    d = load_data()
    u = get_user(d, message.author.id)

    u["xp"] += 10
    need = u["level"] * 100

    if u["xp"] >= need:
        u["xp"] -= need
        u["level"] += 1
        reward = u["level"] * 100
        u["money"] += reward

        await message.channel.send(
            f"🎉 {message.author.mention} 레벨업! Lv.{u['level']}\n💰 +{reward}"
        )

    save_data(d)
    await bot.process_commands(message)

# ===== 지갑 =====
@bot.command()
async def 지갑(ctx):
    u = get_user(load_data(), ctx.author.id)
    await ctx.send(f"💰 {u['money']}코인")

# ===== 출석 =====
@bot.command()
async def 출석(ctx):
    d = load_data()
    u = get_user(d, ctx.author.id)

    today = str(datetime.date.today())

    if u.get("last") == today:
        return await ctx.send("❌ 이미 출석")

    r = random.randint(100, 300)
    u["money"] += r
    u["last"] = today

    save_data(d)
    await ctx.send(f"✅ +{r}")

# ===== 슬롯 =====
@bot.command()
async def 슬롯(ctx, a: int):
    d = load_data()
    u = get_user(d, ctx.author.id)

    if not cd(ctx.author.id, 5):
        return await ctx.send("⏱")

    if a <= 0 or u["money"] < a:
        return await ctx.send("돈 부족")

    s = ["🍒", "🍋", "🔔", "💎", "7️⃣"]
    r = [random.choice(s) for _ in range(3)]

    if r.count(r[0]) == 3:
        w = a * 5
        u["money"] += w
        msg = f"🔥 +{w}"
    else:
        u["money"] -= a
        msg = f"🔴 -{a}"

    save_data(d)
    await ctx.send(f"{'|'.join(r)}\n{msg}")

# ===== 강화 =====
@bot.command()
async def 강화(ctx):
    d = load_data()
    u = get_user(d, ctx.author.id)

    cost = (u["enhance"] + 1) * 200

    if u["money"] < cost:
        return await ctx.send("돈 부족")

    success = random.randint(1, 100) <= 50

    if success:
        u["enhance"] += 1
        msg = f"🔥 성공! +{u['enhance']}"
    else:
        u["enhance"] = max(0, u["enhance"] - 1)
        msg = "💥 실패..."

    u["money"] -= cost
    save_data(d)
    await ctx.send(msg)

# ▶ 실행
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")

    if token is None:
        print("토큰 없음")
    else:
        keep_alive()
        bot.run(token)
