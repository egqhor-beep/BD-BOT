import discord
from discord import app_commands
import sqlite3
from datetime import datetime
from openpyxl import Workbook

# ================= НАСТРОЙКИ =================
TOKEN = "TOKEN"

LOG_CHANNEL_ID = 1463741030963613696
APPLICATION_CHANNEL_ID = 1464741323356770439

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

# ================= SELECT USER VIEW (ИСПРАВЛЕНО) =================
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

    @discord.ui.button(label="Принятие", style=discord.ButtonStyle.success, emoji="➕")
    async def accept(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Принятие", ROLE_ACCEPT), ephemeral=True)

    @discord.ui.button(label="Повышение", style=discord.ButtonStyle.primary, emoji="📈")
    async def promote(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Повышение", ROLE_PROMOTE), ephemeral=True)

    @discord.ui.button(label="Понижение", style=discord.ButtonStyle.secondary, emoji="📉")
    async def demote(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Понижение", ROLE_DEMOTE), ephemeral=True)

    @discord.ui.button(label="Увольнение", style=discord.ButtonStyle.danger, emoji="❌")
    async def fire(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Увольнение", ROLE_FIRE, False), ephemeral=True)

    @discord.ui.button(label="Варн", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def warn(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Предупреждение", ROLE_WARN, False), ephemeral=True)

    @discord.ui.button(label="Снять варн", style=discord.ButtonStyle.success, emoji="🧹")
    async def unwarn(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Снятие предупреждения", ROLE_UNWARN, False), ephemeral=True)

    @discord.ui.button(label="Чёрный список", style=discord.ButtonStyle.danger, emoji="🚫")
    async def blacklist(self, i, b):
        await i.response.send_message("Выберите пользователя:", view=SelectUserView("Черный список", ROLE_BLACKLIST, False), ephemeral=True)


# ================= ЗАЯВКИ (БЕЗ ИЗМЕНЕНИЙ, ВСЁ СОХРАНЕНО) =================
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
        embed.add_field(name="Скилл", value=self.skill.value, inline=False)
        embed.add_field(name="Ожидания", value=self.expectations.value, inline=False)

        await channel.send(embed=embed, view=RecruiterView(interaction.user.id))
        await interaction.response.send_message("✅ Заявка отправлена", ephemeral=True)

class RecruiterView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def interaction_check(self, interaction):
        return has_role(interaction.user, ROLE_RECRUITER)

    @discord.ui.button(label="📥 Взять на рассмотрение")
    async def take(self, interaction, button):
        user = await bot.fetch_user(self.user_id)
        try: await user.send(f"📥 Вашу заявку взял {interaction.user}")
        except: pass
        await interaction.response.send_message("Заявка взята", ephemeral=True)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction, button):
        user = await bot.fetch_user(self.user_id)
        try: await user.send("❌ Ваша заявка отклонена")
        except: pass
        await interaction.response.send_message("Отклонено", ephemeral=True)

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.success)
    async def approve(self, interaction, button):
        guild = interaction.guild
        member = guild.get_member(self.user_id)

        guest = guild.get_role(ROLE_GUEST)
        family = guild.get_role(ROLE_MEMBER)

        if guest in member.roles:
            await member.remove_roles(guest)
        await member.add_roles(family)

        try: await member.send("✅ Ваша заявка одобрена! Добро пожаловать.")
        except: pass

        await interaction.response.send_message("Одобрено", ephemeral=True)

class ApplyView(discord.ui.View):
    @discord.ui.button(label="📩 Отправить заявку в семью")
    async def apply(self, interaction, button):
        await interaction.response.send_modal(ApplicationModal())

@tree.command(name="кнопка_заявки")
async def send_button(interaction):
    await interaction.channel.send("Нажмите кнопку для подачи заявки:", view=ApplyView())
    await interaction.response.send_message("Кнопка отправлена", ephemeral=True)

# ================= КОМАНДЫ =================
@tree.command(name="панель")
async def panel(interaction):
    if not has_role(interaction.user, ROLE_PANEL):
        return await interaction.response.send_message("Нет доступа", ephemeral=True)
    await interaction.response.send_message("Панель управления:", view=AdminPanel(), ephemeral=True)

@tree.command(name="профиль")
async def profile(interaction, user: discord.User):
    cursor.execute("SELECT action, reason, date FROM logs WHERE target_id=?", (user.id,))
    rows = cursor.fetchall()

    if not rows:
        return await interaction.response.send_message("Записей нет", ephemeral=True)

    text = "\n".join(f"[{d}] {a} — {r}" for a, r, d in rows[-10:])
    embed = discord.Embed(title=f"Профиль {user}", description=text)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="очистить_профиль")
async def clear_profile(interaction, user: discord.User):
    if not has_role(interaction.user, ROLE_CLEAR):
        return await interaction.response.send_message("Нет прав", ephemeral=True)
    cursor.execute("DELETE FROM logs WHERE target_id=?", (user.id,))
    conn.commit()
    await interaction.response.send_message("Очищено", ephemeral=True)

@tree.command(name="экспорт")
async def export(interaction):
    if not has_role(interaction.user, ROLE_EXPORT):
        return await interaction.response.send_message("Нет прав", ephemeral=True)

    wb = Workbook()
    ws = wb.active
    ws.append(["Дата", "Действие", "Автор", "Цель", "Ранг", "Причина"])

    cursor.execute("SELECT * FROM logs")
    for _, action, au, t, rank, reason, date in cursor.fetchall():
        ws.append([date, action, au, t, rank, reason])

    wb.save("export.xlsx")
    await interaction.response.send_message(file=discord.File("export.xlsx"), ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    await tree.sync()
    print("Бот запущен")

bot.run(TOKEN)
