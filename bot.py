import discord
from discord import app_commands
import sqlite3
from datetime import datetime
from openpyxl import Workbook

# ================= НАСТРОЙКИ =================
import os
TOKEN = os.getenv("TOKEN")

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

# ================= КОМАНДЫ =================
@tree.command(name="панель")
async def panel(interaction):
    if not has_role(interaction.user, ROLE_PANEL):
        return await interaction.response.send_message("Нет доступа", ephemeral=True)
    await interaction.response.send_message("Панель управления:", view=AdminPanel(), ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    bot.add_view(AdminPanel())
    bot.add_view(ApplyView())
    await tree.sync()
    print("Бот запущен")

bot.run(TOKEN)
