import discord
from discord import app_commands
import sqlite3
from datetime import datetime, timedelta
import asyncio
from openpyxl import Workbook

# ================= НАСТРОЙКИ =================
import os
TOKEN = os.getenv("TOKEN")
print("TOKEN:", TOKEN) 

LOG_CHANNEL_ID = 1463741030963613696
APPLICATION_CHANNEL_ID = 1464741323356770439
MP_LOG_CHANNEL_ID = 1463741030963613696

ROLE_GUEST = 1459109315221786766
ROLE_MEMBER = 1459102595279749231

ROLE_PANEL = [1463266266554040382, 1459105402338803926, 1461038020181626913, 1462540671570284739, 1464168144389017717]
ROLE_ACCEPT = [1463266266554040382, 1459105402338803926, 1461038020181626913, 1462540671570284739, 1464168144389017717]
ROLE_PROMOTE = [1463266266554040382, 1459105402338803926, 1461038020181626913, 1462540671570284739, 1464168144389017717]
ROLE_DEMOTE = [1463266266554040382, 1459105402338803926, 1461038020181626913, 1462540671570284739, 1464168144389017717]
ROLE_FIRE = [1463266266554040382, 1459105402338803926, 1461038020181626913, 1462540671570284739, 1464168144389017717]
ROLE_WARN = [1461038020181626913, 1462540671570284739, 1464168144389017717]
ROLE_UNWARN = [1461038020181626913, 1462540671570284739, 1464168144389017717]
ROLE_BLACKLIST = [1461038020181626913, 1462540671570284739, 1464168144389017717]
ROLE_EXPORT = [1464168144389017717]
ROLE_CLEAR = [1464168144389017717]
ROLE_RECRUITER = [1463266266554040382, 1459105402338803926, 1461038020181626913, 1462540671570284739, 1464168144389017717]
ROLE_MP_ADMIN = [1462540671570284739, 1464168144389017717, 1487147182535610449]
# ============================================

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ================= БАЗА =================
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT,
    author_id INTEGER,
    target_id INTEGER,
    rank_change TEXT,
    reason TEXT,
    date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    nickname TEXT,
    source TEXT,
    skill TEXT,
    expectations TEXT,
    taken_by INTEGER,
    approved_by INTEGER,
    rejected_by INTEGER,
    date TEXT
)
""")
conn.commit()

# ================= УТИЛИТЫ =================
def has_role(member, roles):
    return any(r.id in roles for r in member.roles)

def create_log_embed(action, author, target, rank, reason):
    embed = discord.Embed(title=f"📋 {action}", color=discord.Color.blue())
    embed.add_field(name="Кто:", value=author.mention, inline=False)
    embed.add_field(name="Кого:", value=target.mention, inline=False)

    if rank:
        embed.add_field(name="С какого на какой:", value=rank, inline=False)

    embed.add_field(name="Причина:", value=reason, inline=False)
    embed.set_footer(text=datetime.now().strftime("%d.%m.%Y %H:%M"))
    return embed

# ================= АВТО РОЛЬ =================
@bot.event
async def on_member_join(member):
    role = member.guild.get_role(ROLE_GUEST)
    if role:
        await member.add_roles(role)

# ================= ACTION MODAL =================
class ActionModal(discord.ui.Modal):
    def __init__(self, title, action, target, with_rank=True):
        super().__init__(title=title)
        self.action = action
        self.target = target

        if with_rank:
            self.rank = discord.ui.TextInput(label="С какого на какой")
            self.add_item(self.rank)

        self.reason = discord.ui.TextInput(label="Причина", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction):
        rank = self.rank.value if hasattr(self, "rank") else None
        reason = self.reason.value

        cursor.execute("""
        INSERT INTO logs (action, author_id, target_id, rank_change, reason, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self.action,
            interaction.user.id,
            self.target.id,
            rank,
            reason,
            datetime.now().strftime("%d.%m.%Y %H:%M")
        ))
        conn.commit()

        channel = bot.get_channel(LOG_CHANNEL_ID)
        await channel.send(embed=create_log_embed(self.action, interaction.user, self.target, rank, reason))
        await interaction.response.send_message("✅ Готово", ephemeral=True)

# ================= SELECT USER VIEW =================
class SelectUserView(discord.ui.View):
    def __init__(self, action, roles, with_rank=True):
        super().__init__(timeout=60)
        self.action = action
        self.roles = roles
        self.with_rank = with_rank

        select = discord.ui.UserSelect(
            placeholder="Выберите пользователя",
            min_values=1,
            max_values=1
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if not has_role(interaction.user, self.roles):
            return await interaction.response.send_message("❌ Нет прав", ephemeral=True)

        target = interaction.data["values"][0]
        user = interaction.guild.get_member(int(target))

        await interaction.response.send_modal(
            ActionModal(self.action, self.action, user, self.with_rank)
        )

# ================= ПАНЕЛЬ =================
class AdminPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Принятие", style=discord.ButtonStyle.success, emoji="➕", custom_id="accept_btn")
    async def accept(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Принятие", ROLE_ACCEPT), ephemeral=True)

    @discord.ui.button(label="Повышение", style=discord.ButtonStyle.primary, emoji="📈", custom_id="promote_btn")
    async def promote(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Повышение", ROLE_PROMOTE), ephemeral=True)

    @discord.ui.button(label="Понижение", style=discord.ButtonStyle.secondary, emoji="📉", custom_id="demote_btn")
    async def demote(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Понижение", ROLE_DEMOTE), ephemeral=True)

    @discord.ui.button(label="Увольнение", style=discord.ButtonStyle.danger, emoji="❌", custom_id="fire_btn")
    async def fire(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Увольнение", ROLE_FIRE, False), ephemeral=True)

    @discord.ui.button(label="Варн", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="warn_btn")
    async def warn(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Предупреждение", ROLE_WARN, False), ephemeral=True)

    @discord.ui.button(label="Снять варн", style=discord.ButtonStyle.success, emoji="🧹", custom_id="unwarn_btn")
    async def unwarn(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Снятие предупреждения", ROLE_UNWARN, False), ephemeral=True)

    @discord.ui.button(label="Чёрный список", style=discord.ButtonStyle.danger, emoji="🚫", custom_id="blacklist_btn")
    async def blacklist(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Черный список", ROLE_BLACKLIST, False), ephemeral=True)

    # 🔥 ДОБАВЛЕНО
    @discord.ui.button(label="ЧС без Discord", style=discord.ButtonStyle.secondary, emoji="📄", custom_id="blacklist_no_discord")
    async def blacklist_no_discord(self, interaction, button):
        await interaction.response.send_modal(BlacklistModal())

# ================= ЧС БЕЗ DISCORD =================
class BlacklistModal(discord.ui.Modal, title="ЧС без Discord"):
    static_id = discord.ui.TextInput(label="Static ID")
    nicknames = discord.ui.TextInput(label="Nickname(s)")
    reason = discord.ui.TextInput(label="Причина", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction):
        embed = discord.Embed(title="🚫 Чёрный список (без Discord)", color=discord.Color.red())
        embed.add_field(name="Static ID", value=self.static_id.value, inline=False)
        embed.add_field(name="Nickname(s)", value=self.nicknames.value, inline=False)
        embed.add_field(name="Причина", value=self.reason.value, inline=False)
        embed.add_field(name="Внёс", value=interaction.user.mention, inline=False)
        embed.set_footer(text=datetime.now().strftime("%d.%m.%Y %H:%M"))

        await bot.get_channel(LOG_CHANNEL_ID).send(embed=embed)
        await interaction.response.send_message("Добавлено в ЧС", ephemeral=True)

# ================= ЗАЯВКИ =================
class ApplicationModal(discord.ui.Modal, title="Заявка в семью"):
    nickname = discord.ui.TextInput(label="Ваш ник | Static | Возраст")
    source = discord.ui.TextInput(label="Откуда узнали о нас?")
    skill = discord.ui.TextInput(label="Понимание игры и умение стрелять(0-10)")
    expectations = discord.ui.TextInput(label="Что ждёшь от семьи?", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction):
        cursor.execute("""
        INSERT INTO applications (user_id, nickname, source, skill, expectations, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            interaction.user.id,
            self.nickname.value,
            self.source.value,
            self.skill.value,
            self.expectations.value,
            datetime.now().strftime("%d.%m.%Y %H:%M")
        ))
        conn.commit()

        channel = bot.get_channel(APPLICATION_CHANNEL_ID)

        embed = discord.Embed(title="📩 Новая заявка!")
        embed.add_field(name="Пользователь", value=interaction.user.mention, inline=False)
        embed.add_field(name="Данные", value=self.nickname.value, inline=False)
        embed.add_field(name="Откуда узнал о нас", value=self.source.value, inline=False)
        embed.add_field(name="Скиллы", value=self.skill.value, inline=False)
        embed.add_field(name="Ожидания от семьи", value=self.expectations.value, inline=False)

        await channel.send(embed=embed, view=RecruiterView(interaction.user.id))
        await interaction.response.send_message("✅ Заявка отправлена", ephemeral=True)

class RecruiterView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def interaction_check(self, interaction):
        return has_role(interaction.user, ROLE_RECRUITER)

    @discord.ui.button(label="📥 Взять на рассмотрение", custom_id="take_btn")
    async def take(self, interaction, button):
        await interaction.response.send_message("Заявка взята", ephemeral=True)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id="reject_btn")
    async def reject(self, interaction, button):
        embed = interaction.message.embeds[0]
        embed.add_field(name="❌ Отклонил", value=interaction.user.mention, inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Отклонено", ephemeral=True)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success, custom_id="approve_btn")
    async def approve(self, interaction, button):
        embed = interaction.message.embeds[0]
        embed.add_field(name="✅ Одобрил", value=interaction.user.mention, inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Одобрено", ephemeral=True)

# ================= APPLY =================
class ApplyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Отправить заявку в семью", custom_id="apply_btn")
    async def apply(self, interaction, button):
        await interaction.response.send_modal(ApplicationModal())

@tree.command(name="кнопка_заявки")
async def send_button(interaction):
    await interaction.channel.send("Нажмите кнопку для подачи заявки:", view=ApplyView())
    await interaction.response.send_message("Кнопка отправлена", ephemeral=True)

# ================= МП СИСТЕМА =================
class MPView(discord.ui.View):
    def __init__(self, author, start_time):
        super().__init__(timeout=None)
        self.participants = []
        self.author = author
        self.start_time = start_time
        self.notified = False

    def build_embed(self):
        embed = discord.Embed(
            title=f"МП — начало в {self.start_time.strftime('%H:%M')}",
            color=discord.Color.dark_gray()
        )

        now = datetime.now()
        diff = self.start_time - now

        if diff.total_seconds() > 0:
            minutes = int(diff.total_seconds() // 60)
            embed.add_field(name="До начала", value=f"{minutes} мин.", inline=False)
        else:
            embed.add_field(name="Статус", value="Уже началось", inline=False)

        if not self.participants:
            embed.add_field(name="Участники", value="Список пуст", inline=False)
        else:
            text = "\n".join([f"{i+1}. {u.mention}" for i, u in enumerate(self.participants)])
            embed.add_field(name="Участники", value=text, inline=False)

        embed.set_footer(text=f"Всего: {len(self.participants)}")
        return embed

    async def auto_update(self, message):
        while True:
            await asyncio.sleep(60)

            now = datetime.now()
            diff = (self.start_time - now).total_seconds()

            # 🔔 уведомление за 10 минут
            if diff <= 600 and not self.notified:
                self.notified = True

                for user in self.participants:
                    try:
                        await user.send(
                            f"⏰ МП через 10 минут!\nВремя: {self.start_time.strftime('%H:%M')}"
                        )
                    except:
                        pass

            # 🔄 обновление embed
            try:
                await message.edit(embed=self.build_embed(), view=self)
            except:
                break

            # ⛔ остановка после старта
            if diff <= 0:
                break

    @discord.ui.button(label="Вписаться на капт", style=discord.ButtonStyle.success)
    async def join(self, interaction, button):
        if interaction.user not in self.participants:
            self.participants.append(interaction.user)

        await interaction.message.edit(embed=self.build_embed(), view=self)
        await interaction.response.defer()

    @discord.ui.button(label="Выписаться из списка", style=discord.ButtonStyle.danger)
    async def leave(self, interaction, button):
        if interaction.user in self.participants:
            self.participants.remove(interaction.user)

            diff = (self.start_time - datetime.now()).total_seconds()

            if diff <= 300:
                log_channel = bot.get_channel(MP_LOG_CHANNEL_ID)
                await log_channel.send(
                    f"⚠️ {interaction.user.mention} вышел менее чем за 5 минут до МП"
                )

        await interaction.message.edit(embed=self.build_embed(), view=self)
        await interaction.response.defer()

    @discord.ui.button(label="Проверка на войс", style=discord.ButtonStyle.primary)
    async def voice_check(self, interaction, button):
        if not has_role(interaction.user, ROLE_MP_ADMIN):
            return await interaction.response.send_message("Нет прав", ephemeral=True)

        mentions = " ".join([u.mention for u in self.participants])

        await interaction.channel.send(
            f"📢 МП в {self.start_time.strftime('%H:%M')}!\n{mentions}"
        )
        await interaction.response.defer()

    @discord.ui.button(label="Завершить МП", style=discord.ButtonStyle.secondary)
    async def finish(self, interaction, button):
        if not has_role(interaction.user, ROLE_MP_ADMIN):
            return await interaction.response.send_message("Нет прав", ephemeral=True)

        log_channel = bot.get_channel(MP_LOG_CHANNEL_ID)

        text = "\n".join([f"{i+1}. {u}" for i, u in enumerate(self.participants)])

        embed = discord.Embed(
            title=f"📊 МП завершено ({self.start_time.strftime('%H:%M')})",
            description=text if text else "Нет участников"
        )

        await log_channel.send(embed=embed)

        await interaction.message.delete()
        await interaction.response.send_message("МП завершено", ephemeral=True)

# ================= КОМАНДА =================
@tree.command(name="создать_мп")
@app_commands.describe(time="Время начала (HH:MM)")
async def create_mp(interaction: discord.Interaction, time: str):
    if not has_role(interaction.user, ROLE_MP_ADMIN):
        return await interaction.response.send_message("❌ Нет прав", ephemeral=True)

    try:
        hour, minute = map(int, time.split(":"))
        now = datetime.now()
        start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if start_time < now:
            start_time = start_time.replace(day=now.day + 1)

    except:
        return await interaction.response.send_message("❌ Неверный формат времени (пример: 17:00)", ephemeral=True)

    view = MPView(interaction.user, start_time)
    embed = view.build_embed()

    msg = await interaction.channel.send(embed=embed, view=view)
    bot.loop.create_task(view.auto_update(msg))
    
    await interaction.response.send_message("✅ МП создано", ephemeral=True)
    
# ================= КОМАНДЫ =================
@tree.command(name="панель")
async def panel(interaction):
    if not has_role(interaction.user, ROLE_PANEL):
        return await interaction.response.send_message("Нет доступа", ephemeral=True)
    await interaction.response.send_message("Панель управления:", view=AdminPanel(), ephemeral=True)

# === ВСТАВЬ ЭТО ПОСЛЕ ИНИЦИАЛИЗАЦИИ БАЗЫ ===

@tree.command(name="экспорт")
async def export_logs(interaction: discord.Interaction):
    if not has_role(interaction.user, ROLE_EXPORT):
        return await interaction.response.send_message("❌ Нет прав", ephemeral=True)

    wb = Workbook()
    ws = wb.active
    ws.append(["Action", "Author ID", "Target ID", "Rank", "Reason", "Date"])

    for row in cursor.execute("SELECT action, author_id, target_id, rank_change, reason, date FROM logs"):
        ws.append(row)

    file_name = "logs.xlsx"
    wb.save(file_name)

    await interaction.response.send_message(file=discord.File(file_name))

@tree.command(name="очистить_логи")
async def clear_logs(interaction: discord.Interaction):
    if not has_role(interaction.user, ROLE_CLEAR):
        return await interaction.response.send_message("❌ Нет прав", ephemeral=True)

    cursor.execute("DELETE FROM logs")
    conn.commit()

    await interaction.response.send_message("✅ Логи очищены", ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    bot.add_view(AdminPanel())
    bot.add_view(ApplyView())
    bot.add_view(MPView(None, datetime.now()))

    guild = discord.Object(id=1458525105457070286)
    
    await tree.sync(guild=guild)
    
    print("Бот запущен")

bot.run(TOKEN)
