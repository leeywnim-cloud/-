import discord
from discord.ext import commands
from discord import app_commands
import random, json, os, time, datetime

# ===== 기본 설정 =====
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "data.json"
cooldowns = {}
CHEF_ROLE_ID = 123456789012345678  # ← 셰프 역할 ID 넣기

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
            "money":1000,
            "xp":0,
            "level":1,
            "enhance":0
        }
    return data[uid]

def cd(uid, sec):
    now = time.time()
    if uid in cooldowns and now - cooldowns[uid] < sec:
        return False
    cooldowns[uid] = now
    return True

# ===== 실행 =====
@bot.event
async def on_ready():
    await tree.sync()
    print("봇 ON")

# ===== 경험치 + 명령어 =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    d = load_data()
    u = get_user(d, message.author.id)

    u["xp"] += 10

    if u["xp"] >= u["level"] * 100:
        u["xp"] = 0
        u["level"] += 1
        reward = u["level"] * 100
        u["money"] += reward

        await message.channel.send(
            f"🎉 {message.author.mention} Lv.{u['level']}!\n💰 +{reward}"
        )

    save_data(d)
    await bot.process_commands(message)

# ===== 지갑 =====
@bot.command()
async def 지갑(ctx):
    u = get_user(load_data(), ctx.author.id)
    await ctx.send(f"💰 {u['money']}")

@tree.command(name="지갑")
async def wallet(i: discord.Interaction):
    u = get_user(load_data(), i.user.id)
    await i.response.send_message(f"💰 {u['money']}")

# ===== 출석 =====
@bot.command()
async def 출석(ctx):
    d = load_data()
    u = get_user(d, ctx.author.id)

    today = str(datetime.date.today())
    if u.get("last") == today:
        return await ctx.send("❌ 이미 출석")

    r = random.randint(100,300)
    u["money"] += r
    u["last"] = today

    save_data(d)
    await ctx.send(f"✅ +{r}")

@tree.command(name="출석")
async def slash_att(i: discord.Interaction):
    d = load_data()
    u = get_user(d, i.user.id)

    today = str(datetime.date.today())
    if u.get("last") == today:
        return await i.response.send_message("❌ 이미 출석")

    r = random.randint(100,300)
    u["money"] += r
    u["last"] = today

    save_data(d)
    await i.response.send_message(f"✅ +{r}")

# ===== 슬롯 =====
@bot.command()
async def 슬롯(ctx, a:int):
    d = load_data()
    u = get_user(d, ctx.author.id)

    if not cd(ctx.author.id,5):
        return await ctx.send("⏱ 쿨타임")

    if a<=0 or u["money"]<a:
        return await ctx.send("돈 부족")

    s=["🍒","🍋","🔔"]
    r=[random.choice(s) for _ in range(3)]

    if r.count(r[0])==3:
        win=a*3
        u["money"]+=win
        msg=f"🔥 +{win}"
    else:
        u["money"]-=a
        msg=f"🔴 -{a}"

    save_data(d)
    await ctx.send(f"{r}\n{msg}")

# ===== 강화 =====
@bot.command()
async def 강화(ctx):
    d = load_data()
    u = get_user(d, ctx.author.id)

    cost = (u["enhance"]+1)*200

    if u["money"] < cost:
        return await ctx.send("돈 부족")

    if random.random() < 0.5:
        u["enhance"] += 1
        msg = f"🔥 성공! +{u['enhance']}"
    else:
        u["enhance"] = 0
        msg = "💀 터짐"

    u["money"] -= cost
    save_data(d)
    await ctx.send(msg)

@tree.command(name="강화")
async def slash_enhance(i: discord.Interaction):
    d = load_data()
    u = get_user(d, i.user.id)

    cost = (u["enhance"]+1)*200

    if u["money"] < cost:
        return await i.response.send_message("돈 부족")

    if random.random() < 0.5:
        u["enhance"] += 1
        msg = f"🔥 성공! +{u['enhance']}"
    else:
        u["enhance"] = 0
        msg = "💀 터짐"

    u["money"] -= cost
    save_data(d)
    await i.response.send_message(msg)

# ===== 랭킹 =====
@bot.command()
async def 랭킹(ctx):
    d = load_data()
    s = sorted(d.items(), key=lambda x:x[1]["money"], reverse=True)

    msg="🏆 돈 랭킹\n"
    for i,(uid,data) in enumerate(s[:5],1):
        user = await bot.fetch_user(int(uid))
        msg += f"{i}. {user.name} - {data['money']}\n"

    await ctx.send(msg)

@tree.command(name="랭킹")
async def slash_rank(i: discord.Interaction):
    d = load_data()
    s = sorted(d.items(), key=lambda x:x[1]["money"], reverse=True)

    msg="🏆 돈 랭킹\n"
    for idx,(uid,data) in enumerate(s[:5],1):
        user = await bot.fetch_user(int(uid))
        msg += f"{idx}. {user.name} - {data['money']}\n"

    await i.response.send_message(msg)

# ===== 주문 (셰프 멘션) =====
@bot.command()
async def 주문(ctx, *, item:str):
    d = load_data()
    u = get_user(d, ctx.author.id)

    cost = random.randint(100,300)

    if u["money"] < cost:
        return await ctx.send("돈 부족")

    u["money"] -= cost
    save_data(d)

    role = ctx.guild.get_role(CHEF_ROLE_ID)

    await ctx.send(
        f"🍽️ {ctx.author.mention} 주문: {item}\n💰 -{cost}\n{role.mention}",
        allowed_mentions=discord.AllowedMentions(roles=True)
    )

@tree.command(name="주문")
@app_commands.describe(아이템="주문할 것")
async def slash_order(i: discord.Interaction, 아이템:str):
    d = load_data()
    u = get_user(d, i.user.id)

    cost = random.randint(100,300)

    if u["money"] < cost:
        return await i.response.send_message("돈 부족")

    u["money"] -= cost
    save_data(d)

    role = i.guild.get_role(CHEF_ROLE_ID)

    await i.response.send_message(
        f"🍽️ {i.user.mention} 주문: {아이템}\n💰 -{cost}\n{role.mention}",
        allowed_mentions=discord.AllowedMentions(roles=True)
    )

# ===== 실행 =====
bot.run("여기에_토큰")