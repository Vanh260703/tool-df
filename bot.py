"""Bot Discord tìm lại code build súng đã đăng trong channel.

/build k437   -> các build K437 mới nhất
!k437         -> lối tắt, giống hệt /build k437
"""
import logging
import os
import sqlite3

import discord
from discord import app_commands
from dotenv import load_dotenv

from buildcode import extract_builds, normalize

load_dotenv()
TOKEN = os.environ["DISCORD_TOKEN"]
WATCH_CHANNEL_IDS = {int(x) for x in os.environ["WATCH_CHANNEL_IDS"].split(",") if x.strip()}
GUILD_ID = int(os.environ["GUILD_ID"]) if os.environ.get("GUILD_ID") else None
DB_PATH = os.environ.get("DB_PATH", "builds.db")
MAX_RESULTS = 10

log = logging.getLogger("df-bot")

db = sqlite3.connect(DB_PATH)
db.executescript("""
CREATE TABLE IF NOT EXISTS builds (
    message_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    author     TEXT,
    created_at INTEGER,
    weapon     TEXT,
    mode       TEXT,
    note       TEXT,
    code       TEXT NOT NULL,
    search     TEXT NOT NULL,
    jump_url   TEXT,
    UNIQUE (message_id, code)
);
CREATE INDEX IF NOT EXISTS idx_builds_created ON builds (created_at DESC);
CREATE TABLE IF NOT EXISTS state (channel_id INTEGER PRIMARY KEY, last_message_id INTEGER);
""")


def index_message(msg: discord.Message) -> int:
    builds = extract_builds(msg.content)
    for b in builds:
        search = b.search_text()
        db.execute(
            "INSERT OR IGNORE INTO builds VALUES (?,?,?,?,?,?,?,?,?,?)",
            (msg.id, msg.channel.id, msg.author.display_name, int(msg.created_at.timestamp()),
             b.weapon, b.mode, b.note, b.code, search, msg.jump_url),
        )
    db.execute(
        "INSERT INTO state VALUES (?,?) ON CONFLICT(channel_id) DO UPDATE SET "
        "last_message_id = MAX(last_message_id, excluded.last_message_id)",
        (msg.channel.id, msg.id),
    )
    db.commit()
    return len(builds)


def search_builds(query: str, mode: str | None = None) -> tuple[int, list[sqlite3.Row]]:
    where, params = "search LIKE ?", [f"%{normalize(query)}%"]
    if mode:
        where += " AND search LIKE ?"
        params.append(f"%{normalize(mode)}%")
    total = db.execute(f"SELECT COUNT(*) FROM builds WHERE {where}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT weapon, mode, note, code, author, created_at, jump_url FROM builds "
        f"WHERE {where} ORDER BY created_at DESC LIMIT ?",
        [*params, MAX_RESULTS],
    ).fetchall()
    return total, rows


def results_embed(query: str, total: int, rows) -> discord.Embed:
    if not rows:
        return discord.Embed(description=f"Không tìm thấy build nào cho **{query}**.", color=0xE74C3C)
    embed = discord.Embed(
        title=f"Build {query.upper()}",
        description=f"Tìm thấy {total} build, hiện {len(rows)} build mới nhất.",
        color=0x2ECC71,
    )
    for weapon, mode, note, code, author, created_at, jump_url in rows:
        name = " · ".join(x for x in (weapon or "Không rõ súng", mode, note and f"“{note[:60]}”") if x)
        embed.add_field(
            name=name[:256],
            value=f"```{code}```{author} · <t:{created_at}:d> · [Xem tin nhắn]({jump_url})",
            inline=False,
        )
    return embed


class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # bắt buộc để đọc code trong tin nhắn
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.backfilled = False

    async def setup_hook(self):
        if GUILD_ID:  # sync theo server thì lệnh hiện ngay, sync global mất tới 1 giờ
            guild = discord.Object(GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        log.info("Đăng nhập: %s", self.user)
        if self.backfilled:  # on_ready chạy lại mỗi lần reconnect
            return
        self.backfilled = True
        for channel_id in WATCH_CHANNEL_IDS:
            channel = self.get_channel(channel_id) or await self.fetch_channel(channel_id)
            row = db.execute("SELECT last_message_id FROM state WHERE channel_id = ?", (channel_id,)).fetchone()
            after = discord.Object(row[0]) if row else None
            found = 0
            async for msg in channel.history(limit=None, after=after, oldest_first=True):
                found += index_message(msg)
            log.info("Quét #%s: thêm %d code", channel, found)

    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        if msg.channel.id in WATCH_CHANNEL_IDS:
            index_message(msg)
        if msg.content.startswith("!") and len(msg.content) > 1:
            query = msg.content[1:].strip()
            total, rows = search_builds(query)
            if not rows:  # im lặng để không đụng lệnh "!" của bot khác
                return
            await msg.reply(embed=results_embed(query, total, rows), mention_author=False)

    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.channel_id not in WATCH_CHANNEL_IDS:
            return
        db.execute("DELETE FROM builds WHERE message_id = ?", (payload.message_id,))
        channel = self.get_channel(payload.channel_id)
        index_message(await channel.fetch_message(payload.message_id))

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        db.execute("DELETE FROM builds WHERE message_id = ?", (payload.message_id,))
        db.commit()


bot = Bot()


@bot.tree.command(name="build", description="Tìm code build theo tên súng")
@app_commands.describe(weapon="Tên súng, vd: k437, m4a1, ci-19", mode="Lọc theo chế độ (tuỳ chọn)")
async def build_cmd(interaction: discord.Interaction, weapon: str, mode: str | None = None):
    total, rows = search_builds(weapon, mode)
    await interaction.response.send_message(embed=results_embed(weapon, total, rows))


@build_cmd.autocomplete("weapon")
async def weapon_autocomplete(interaction: discord.Interaction, current: str):
    rows = db.execute(
        "SELECT weapon, COUNT(*) n FROM builds WHERE weapon IS NOT NULL GROUP BY weapon ORDER BY n DESC"
    ).fetchall()
    needle = normalize(current)
    return [
        app_commands.Choice(name=f"{w} ({n})"[:100], value=w[:100])
        for w, n in rows if needle in normalize(w)
    ][:25]


if __name__ == "__main__":
    bot.run(TOKEN, root_logger=True)
