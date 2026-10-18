# ═══════════════════════════════════════════════════════════════════════
#   LUFFY CREW - ULTIMATE MULTI BOT TELEGRAM SCRIPT
#   v5.4 FINAL WORKING | 72 Commands | Zero Crashes | Zero Duplicates
# ═══════════════════════════════════════════════════════════════════════

import os, sys, json, time, random, asyncio, logging, re
import aiohttp, psutil
from datetime import datetime, timezone, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Set, Optional, Any, Tuple
from urllib.parse import quote

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, Bot
)
from telegram.ext import (
    Application, ApplicationBuilder, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, BaseHandler
)
from telegram.error import TelegramError, RetryAfter, Forbidden, BadRequest
from telegram.constants import ParseMode

try:
    from telegram import ReactionTypeEmoji
    HAS_REACTIONS = True
except ImportError:
    ReactionTypeEmoji = None
    HAS_REACTIONS = False

try:
    GROUP_FILTER = filters.ChatType.GROUPS
except AttributeError:
    GROUP_FILTER = filters.ChatType.GROUP | filters.ChatType.SUPERGROUP

# ═══════════════════════════════════════════════════════════════════════
#   CONFIG
# ═══════════════════════════════════════════════════════════════════════

BOT_TOKEN = os.getenv("BOT_TOKEN", "8965163421:AAEG4o91dJ3-v00FzRUYWcVlTcR-K_dk95o")
OWNER_ID  = int(os.getenv("OWNER_ID", "8783373485"))

SUDO_FILE, BOTS_FILE, TARGETS_FILE = "sudo_users.json", "bots.json", "targets.json"
PFP_FILE, CONFIG_FILE = "pfp_loop.json", "config.json"

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("LUFFY")
START_TIME = time.time()

AUTHORIZATION_MSG = (
    "𓆩💢𓆪 𝐎ɴʟʏ 𓆩🕸️⃟𓆪  ⟨⟨•°𝐋ᴜꜰꜰʏ ⪻ 🎀 ⪼ ⟩⟩ "
    "𓆩🎀⃟𓆪 𝐇ᴀꜱ 𝐀ᴜᴛʜᴏʀɪᴛʏ 𝐓ᴏ 𝐅ᴜᴄᴋ 𝐘ᴏᴜʀ 𝐌ᴏᴍ 𓆩💢𓆪"
)

DEFAULT_MENU_HEADER = (
    "╔══════════════════════════════╗\n"
    "   🏴‍☠️  𝗟𝗨𝗙𝗙𝗬 𝗖𝗥𝗘𝗪 𝗔𝗥𝗘 𝗥𝗘𝗔𝗗𝗬  🏴‍☠️\n"
    "╚══════════════════════════════╝\n\n"
    "🔥 𝐌𝐔𝐋𝐓𝐈-𝐁𝐎𝐓 𝐂𝐎𝐍𝐓𝐑𝐎𝐋𝐋𝐄𝐑 🔥\n\n"
    "➤ ᴘʟᴇᴀꜱᴇ ᴀᴅᴅ ᴍᴏʀᴇ ʙᴏᴛꜱ ʙʏ ᴛᴀᴘᴘɪɴɢ ᴏɴ ᴀᴅᴅ ᴛᴏᴋᴇɴ/ʙᴏᴛꜱ\n"
    "➤ ᴀʟʟ ꜰᴇᴀᴛᴜʀᴇꜱ ᴡᴏʀᴋ ɪɴ ɪɴʟɪɴᴇ ʙᴜᴛᴛᴏɴꜱ\n"
    "➤ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜꜱᴇʀꜱ ᴡɪʟʟ ʙᴇ ʙʟᴏᴄᴋᴇᴅ 🚫\n"
)

CFG = {
    "start_text": DEFAULT_MENU_HEADER,
    "start_media_type": None,
    "start_media_file_id": None,
    "game_over_media": "https://files.catbox.moe/flcgis.mp4",
    "game_over_type": "video",
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                d = json.load(f)
            for k in CFG:
                if k in d: CFG[k] = d[k]
    except Exception as e:
        log.warning(f"config load: {e}")

def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(CFG, f, indent=2)
    except: pass

load_config()

DEFAULT_INTERVALS = {"nc": 0.1, "spam": 0.02, "raid": 0.05, "pfp": 0.1, "slide": 0.01}
CHAT_INTERVALS: Dict[int, Dict[str, float]] = defaultdict(dict)

def get_interval(chat_id: int, key: str) -> float:
    return CHAT_INTERVALS.get(chat_id, {}).get(key, DEFAULT_INTERVALS.get(key, 0.1))

def set_interval(chat_id: int, key: str, value: float):
    if key == "all":
        for k in DEFAULT_INTERVALS: CHAT_INTERVALS[chat_id][k] = value
    else:
        CHAT_INTERVALS[chat_id][key] = value

_bot_cooldown: Dict[int, float] = defaultdict(float)

def _cooldown_ok(bot_id: int) -> bool:
    return time.monotonic() >= _bot_cooldown.get(bot_id, 0)

def _set_cooldown(bot_id: int, seconds: float):
    _bot_cooldown[bot_id] = time.monotonic() + seconds

INVIS_SUFFIXES = ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff",
                  "\u00ad", "\u034f", "\u3164", "\u17b4", "\u17b5"]

# ═══════════════════════════════════════════════════════════════════════
#   DOT-PREFIX COMMAND HANDLER (FIXED — super().__init__() + block)
# ═══════════════════════════════════════════════════════════════════════

class DotCommandHandler(BaseHandler):
    def __init__(self, command, callback, filters_=None):
        super().__init__()  # ⚠️ CRITICAL: PTB BaseHandler init
        self.commands = [command.lower()] if isinstance(command, str) else [c.lower() for c in command]
        self.callback = callback
        self.filters_ = filters_
        self.block = True  # ⚠️ CRITICAL: Dispatcher property

    def check_update(self, update):
        if not isinstance(update, Update) or not update.effective_message: return None
        msg = update.effective_message
        text = msg.text or msg.caption or ""
        if not text.startswith("."): return None
        if self.filters_ and not self.filters_(update): return None
        parts = text.split("\n", 1)[0].split()
        if not parts: return None
        cmd = parts[0][1:].split("@")[0].lower()
        if cmd not in self.commands: return None
        return parts[1:] if len(parts) > 1 else []

    async def handle_update(self, update, application, check_result, context):
        if check_result is not None: context.args = check_result
        return await self.callback(update, context)

# ═══════════════════════════════════════════════════════════════════════
#   ULTRA GUARD
# ═══════════════════════════════════════════════════════════════════════

class UltraGuard:
    GLOBAL_RATE, GLOBAL_BURST = 30.0, 64
    def __init__(self, bot_id):
        self.bot_id = bot_id
        self.rate = self.GLOBAL_RATE
        self.capacity = float(self.GLOBAL_BURST)
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()
        self._lk = asyncio.Lock()
        self._flood_until = 0.0
        self._successes, self._failures = 0, 0
        self._last_error = ""

    async def _gate(self):
        async with self._lk:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.last_refill) * self.rate)
            self.last_refill = now
            wait = max(0.0, (1.0 - self.tokens) / self.rate if self.tokens < 1 else 0.0)
            if self._flood_until > now:
                wait = max(wait, self._flood_until - now)
            if wait > 0:
                await asyncio.sleep(wait)
                self.last_refill = time.monotonic()
            self.tokens = max(0.0, self.tokens - 1.0)

    @property
    def delay(self): return max(0.0, self._flood_until - time.monotonic())

    def stats(self):
        return {"rate": self.rate, "tokens": self.tokens, "successes": self._successes,
                "failures": self._failures, "last_error": self._last_error}

_guards: Dict[int, UltraGuard] = {}
def get_guard(bot_id):
    if bot_id not in _guards: _guards[bot_id] = UltraGuard(bot_id)
    return _guards[bot_id]

async def safe_call(fn, *a, bot_id=None, timeout=1.5, **kw):
    if bot_id is not None and not _cooldown_ok(bot_id): return None
    try:
        return await asyncio.wait_for(fn(*a, **kw), timeout=timeout)
    except asyncio.TimeoutError:
        if bot_id is not None: _set_cooldown(bot_id, 2.0)
        return None
    except RetryAfter as e:
        if bot_id is not None: _set_cooldown(bot_id, float(e.retry_after))
        return None
    except (Forbidden, BadRequest): return None
    except Exception: return None

async def safe_edit(q, text, reply_markup=None, parse_mode=None):
    chat_id = q.message.chat.id
    msg_id = q.message.message_id
    bot = q.bot
    if q.message.text is not None:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id,
                text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        except BadRequest as e:
            if "not modified" in str(e).lower(): return True
        except Exception: pass
    if (q.message.caption is not None or q.message.photo
        or q.message.video or q.message.animation):
        try:
            await bot.edit_message_caption(chat_id=chat_id, message_id=msg_id,
                caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        except BadRequest as e:
            if "not modified" in str(e).lower(): return True
        except Exception: pass
    try:
        await bot.send_message(chat_id=chat_id, text=text,
            reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Exception: return False

# ═══════════════════════════════════════════════════════════════════════
#   CHILD BOT MANAGER
# ═══════════════════════════════════════════════════════════════════════

class ChildBotManager:
    def __init__(self):
        self.bots: Dict[int, Dict] = {}
        self._lock = asyncio.Lock()

    def save(self):
        try:
            data = [{"token": e["token"], "username": e["username"], "id": e["id"]}
                    for e in self.bots.values()]
            with open(BOTS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except: pass

    def load_tokens(self):
        try:
            if os.path.exists(BOTS_FILE):
                with open(BOTS_FILE) as f:
                    return json.load(f)
        except: pass
        return []

    async def add_and_start(self, token: str) -> Dict:
        token = token.strip()
        if not token or ":" not in token:
            raise ValueError("Invalid token format")
        async with self._lock:
            probe = Bot(token=token)
            me = await probe.get_me()
            if me.id in self.bots:
                return {**self.bots[me.id], "_existed": True}
            app = ApplicationBuilder().token(token).build()
            register_child_handlers(app)
            try:
                await app.initialize()
                await app.start()
                await app.updater.start_polling(drop_pending_updates=True)
            except Exception:
                try: await app.shutdown()
                except: pass
                raise
            entry = {"token": token, "username": me.username, "id": me.id,
                     "bot": app.bot, "app": app}
            self.bots[me.id] = entry
            self.save()
            log.info(f"✅ Child bot @{me.username} started")
            return {**entry, "_existed": False}

    async def stop_and_remove(self, identifier) -> Optional[str]:
        async with self._lock:
            entry = None
            if isinstance(identifier, int):
                entry = self.bots.get(identifier)
            else:
                target = str(identifier).lower().lstrip("@")
                for b in self.bots.values():
                    if b["username"].lower() == target or str(b["id"]) == target:
                        entry = b; break
            if not entry: return None
            uname = entry["username"]
            app = entry["app"]
            try: await app.updater.stop()
            except: pass
            try: await app.stop()
            except: pass
            try: await app.shutdown()
            except: pass
            del self.bots[entry["id"]]
            self.save()
            log.info(f"🗑️ Child bot @{uname} stopped")
            return uname

    async def start_all_from_disk(self):
        for entry in self.load_tokens():
            try:
                await self.add_and_start(entry["token"])
            except Exception as e:
                log.warning(f"❌ Failed to start @{entry.get('username', '?')}: {e}")

    async def stop_all(self):
        for app in [e["app"] for e in self.bots.values()]:
            try: await app.updater.stop()
            except: pass
        for app in [e["app"] for e in self.bots.values()]:
            try: await app.stop()
            except: pass
        for app in [e["app"] for e in self.bots.values()]:
            try: await app.shutdown()
            except: pass
        self.bots.clear()

    def get_all(self) -> List[Dict]:
        return list(self.bots.values())

CHILD_MGR = ChildBotManager()

def all_bots() -> List[Dict]:
    return CHILD_MGR.get_all()

# ═══════════════════════════════════════════════════════════════════════
#   SUDO
# ═══════════════════════════════════════════════════════════════════════

SUDO_USERS: Set[int] = set()

def load_sudo():
    global SUDO_USERS
    try:
        if os.path.exists(SUDO_FILE):
            with open(SUDO_FILE) as f:
                SUDO_USERS = set(json.load(f).get("users", []))
    except: SUDO_USERS = set()

def save_sudo():
    try:
        with open(SUDO_FILE, "w") as f:
            json.dump({"users": list(SUDO_USERS)}, f)
    except: pass

load_sudo()

def is_authorized(uid): return uid == OWNER_ID or uid in SUDO_USERS

def only_sudo(func):
    async def w(update, context):
        if not update.effective_user: return
        if not is_authorized(update.effective_user.id):
            try:
                if update.callback_query:
                    try:
                        await update.callback_query.answer(
                            "🚫 Unauthorized — you are not sudo", show_alert=True)
                    except Exception: pass
                m = update.effective_message or (
                    update.callback_query.message if update.callback_query else None)
                if m: await m.reply_text(AUTHORIZATION_MSG)
            except Exception: pass
            return
        return await func(update, context)
    return w

def only_owner(func):
    async def w(update, context):
        if not update.effective_user: return
        if update.effective_user.id != OWNER_ID:
            try:
                if update.callback_query:
                    try:
                        await update.callback_query.answer("🚫 Only owner", show_alert=True)
                    except Exception: pass
                m = update.effective_message or (
                    update.callback_query.message if update.callback_query else None)
                if m: await m.reply_text("🚫 ᴏɴʟʏ ꜱᴇʀᴠᴇʀ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛꜱ ꜱʜʏᴛ ¡!")
            except Exception: pass
            return
        return await func(update, context)
    return w

# ═══════════════════════════════════════════════════════════════════════
#   STATE
# ═══════════════════════════════════════════════════════════════════════

ACTIVE_TASKS: Dict[int, str] = {}
TARGETS: Dict[int, str] = {}
TARGETS_REV: Dict[int, int] = {}
NAMED_TASKS: Dict[int, Dict[str, List[asyncio.Task]]] = defaultdict(lambda: defaultdict(list))
SLIDE_TRACKERS: Dict[int, List[Dict]] = defaultdict(list)
CHAT_LOCKS: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
LAST_MSG: Dict[Tuple[int, str], int] = {}

def _track(cid, name, task): NAMED_TASKS[cid][name.lower()].append(task)

def _cancel_named(cid, name) -> int:
    name = name.lower()
    tasks = NAMED_TASKS.get(cid, {}).get(name, [])
    n = 0
    for t in tasks:
        if not t.done():
            try: t.cancel(); n += 1
            except: pass
    NAMED_TASKS[cid][name] = []
    return n

def _cancel_all_named(cid) -> int:
    n = 0
    for name in list(NAMED_TASKS.get(cid, {}).keys()):
        n += _cancel_named(cid, name)
    return n

async def claim_and_start_multi(cid: int, cmd: str, msg_id: int, task_factory) -> bool:
    lock = CHAT_LOCKS[cid]
    async with lock:
        prev = LAST_MSG.get((cid, cmd), 0)
        if msg_id <= prev: return False
        LAST_MSG[(cid, cmd)] = msg_id
        _cancel_named(cid, cmd)
        tasks = task_factory()
        for t in tasks: _track(cid, cmd, t)
        return True

async def claim_once(cid: int, cmd: str, msg_id: int) -> bool:
    lock = CHAT_LOCKS[cid]
    async with lock:
        prev = LAST_MSG.get((cid, cmd), 0)
        if msg_id <= prev: return False
        LAST_MSG[(cid, cmd)] = msg_id
        return True

# ═══════════════════════════════════════════════════════════════════════
#   TARGETS
# ═══════════════════════════════════════════════════════════════════════

def load_targets():
    global TARGETS, TARGETS_REV
    try:
        if os.path.exists(TARGETS_FILE):
            with open(TARGETS_FILE) as f:
                d = json.load(f)
            TARGETS = {int(k): v for k, v in d.get("by_id", {}).items()}
            TARGETS_REV = {int(k): v for k, v in d.get("by_label", {}).items()}
    except: pass

def save_targets():
    try:
        with open(TARGETS_FILE, "w") as f:
            json.dump({"by_id": {str(k): v for k, v in TARGETS.items()},
                       "by_label": {str(k): v for k, v in TARGETS_REV.items()}}, f)
    except: pass

load_targets()

def _label_to_uid(label):
    if not label: return None
    for uid, lbl in TARGETS.items():
        if lbl.lower() == label.lower(): return uid
    return None

async def _resolve_target(chat_id, bot, args):
    if not args: return ""
    uid = _label_to_uid(args[0])
    if uid is None: return " ".join(args)
    try:
        member = await bot.get_chat_member(chat_id, uid)
        u = member.user
        mention = f"@{u.username}" if u.username else u.first_name
        rest = " ".join(args[1:])
        return (mention + (" " + rest if rest else "")).strip()
    except: return " ".join(args)

# ═══════════════════════════════════════════════════════════════════════
#   PFP STATE
# ═══════════════════════════════════════════════════════════════════════

PFP_LOOP_STATE: Dict[int, bool] = {}
PFP_IMAGES: Dict[int, List[str]] = defaultdict(list)

def load_pfp():
    global PFP_LOOP_STATE, PFP_IMAGES
    try:
        if os.path.exists(PFP_FILE):
            with open(PFP_FILE) as f:
                d = json.load(f)
            PFP_LOOP_STATE = {int(k): v for k, v in d.get("state", {}).items()}
            PFP_IMAGES = {int(k): list(v) for k, v in d.get("images", {}).items()}
    except: pass

def save_pfp():
    try:
        with open(PFP_FILE, "w") as f:
            json.dump({"state": {str(k): v for k, v in PFP_LOOP_STATE.items()},
                       "images": {str(k): list(v) for k, v in PFP_IMAGES.items()}}, f)
    except: pass

load_pfp()

# ═══════════════════════════════════════════════════════════════════════
#   TEMPLATES (all preserved)
# ═══════════════════════════════════════════════════════════════════════

LUFFY_EMOJI = [
    ["🌑","🌒","🌓","🌔","🌕","🌖","🌗","🌘","🌙","🌚","🌝","🌛","🌜"],
    ["☠️","👾","🫐","✨","🖤","🤍","💖","❤️‍🔥","🌺","🌷","🌸","🛸","🧃","🍌","🍁","🌿","🍀","🔥","🌋","🌊","❄️","🌈","🪐","🪼"],
    ["🥱","😱","🤨","😒","😡","🤬","😤","😮‍💨","🥵","🥶","🤢","🤮","🫩","😈","👿","👽","🧃","🧋","🗻","🃏","💠","🇦🇨","🇦🇩","🇦🇪"],
    ["🇦🇨","🇦🇩","🇦🇪","🇦🇫","🇦🇬","🇦🇮","🇦🇱","🇦🇲","🇦🇴","🇦🇶","🇦🇷","🇦🇸","🇦🇹","🇦🇺","🇦🇼","🇧🇦","🇧🇶","🇧🇱","🇧🇫","🇨🇮","🇨🇩","🇨🇦","🇨🇿","🇩🇯","🇨🇭","🇪🇬","🇨🇨","🇧🇯","🇧🇶","🇰🇿","🇰🇼","🇰🇳","🇲🇭","🇲🇪","🇲🇬","🇰🇳","🇮🇴","🇯🇵","🇷🇺","🇳🇺","🇵🇬","🇸🇩","🇵🇷","🇵🇳","🇵🇭","🇳🇫","🇳🇪","🇺🇾","🇺🇸","🇻🇪"],
    ["🌟","💫","✨","🌈","🦋","🌸","🎀","🕊️","🌺","🌷","🌠","☄️","👾","💢","🕸️","🗿","💸","🔮","📿","🚬"],
    ["❤️","🧡","💛","💚","💙","💜","🖤","🤍","🤎","🩷","🩵","💚","🩶","💔","❣️","💕","💞","💓","💗","💖","💘","💝"],
    ["🌬️","❄️","🌀","🌪️","⚡","☔","🌈","💧","☁️","🌨️","🌧️","🌩️","⛈️","🌦️","🌥️","⛅"],
    ["🐶","🐰","🐻‍❄️","🐮","🐵","🐒","🐤","🐱","🦊","🐭","🐻","🐹","🐼","🐸","🦁","🐯","🐥","🪿","🐦","🐣"],
    ["🦋⃟🌑","🦋⃟🌒","🦋⃟🌔","🦋⃟🌕","🦋⃟🌖","🦋⃟🌗","🦋⃟🌘","🦋⃟🪐","🦋⃟🌍","🦋⃟🌎","🦋⃟🌙","🦋⃟☄️","🦋⃟🫧"],
    ["🪠","🪒","🪫","🪸","🪷","🪹","🪺","🫧","🫘","🫚","🫛","🪮","🪭"],
]
LUFFY_WORDS = ["𝗧ᴍᴋʙ","𝗧ᴍᴋᴄ","𝗥ᴀɴᴅ","𝗕ᴋʟ","𝗧ᴍʀ","𝗟ᴜɴ𝗞ʜᴀ","𝗠ᴀᴅᴇʀᴄʜᴏᴅ","𝗕ꜱᴅᴋ",
               "𝗚ᴀɴᴅᴜ","𝗧ᴍᴋᴄ𝗠ᴀᴄᴄʜᴀʀ","𝗣ʟᴀʏ𝗚ɪʀʟ","𝗔ꜱꜱ𝗛ᴏʟᴇ","𝗡ɪɢɢᴀ",
               "𝗙ᴜᴄᴋ𝗬ᴏᴜ","𝗣ᴇʀᴠᴇʀᴛ","𝗦ᴛᴇᴘꜱɪꜱ","𝗠ᴏᴛʜᴇʀ𝗙ᴜᴄᴋᴇʀ","𝗕ᴏʙʙɪᴇ",
               "𝗕ᴀꜱᴛᴀʀᴅ","𝗣ɪᴇᴄᴇ𝗢ꜰ𝗦ʜɪᴛ"]

def _rep(s, n): return s * n

def build_luffy_nc(n, text):
    emj = random.choice(LUFFY_EMOJI[(n-1) % len(LUFFY_EMOJI)])
    if n == 1: return f"•{emj}• {text} {random.choice(LUFFY_WORDS)} " + _rep("𒈙🦋🌙⃤", 128)
    if n == 2: return f"≼ {emj} ≽ {text} ʟꪊꪀᴅ ᥴʜᴜડ " + _rep("🈲∿∿∿", 20) + "🈲∿∿∿"
    if n == 3: return f"⪻{emj}⪼ {text} ⪻{emj}⪼"
    if n == 4: return f"⊱{emj}⊰ {text} {_rep('ᥫ᭡.🌏', 20)} ⊱{emj}⊰"
    if n == 5: return f"𓆩{emj}𓆪 {text} MADARCH⭕️D {_rep('༻༺🩷', 40)} 𓆩{emj}𓆪"
    if n == 6: return f"«{emj}» {text} ᴛᴍᴋᴄ " + "".join(f"——({emj})" for _ in range(40)) + f" «{emj}»"
    if n == 7: return f"<<{emj}>> {text} <<{emj}>>"
    if n == 8: return f"{emj} {text} {_rep('ဪ🟪🟩🟪🟩🟡🔵ဪဪဪ', 8)} {emj}"
    if n == 9: return f"({emj}) {text} ———🌙"
    if n == 10: return f"[{emj}] {text} 𝐋ᴜғғʏ Bһᴀɢᴡᴀꪀ है ~//~  🦢💘"
    return text

VEGETA_EMOJI = [
    ["😀","😃","😄","😁","😂","😅","🥹","😆","🤣","🥲","☺️","😊"],
    ["🍏","🍋","🍎","🍐","🍊","🍈","🫐","🍉","🍓","🍇"],
    ["🪬","🧿","🪞","🪆","🪩","🗿","🪦","🪚","🪓","🪤","🪱","🪰"],
    ["😺","😸","😹","😻","😼","😽","🙀","😿","😾"],
    ["🕛","🕧","🕐","🕜","🕑","🕝","🕒","🕞","🕓","🕟","🕔","🕠","🕕","🕡","🕖","🕢","🕗","🕣","🕘","🕤"],
]

def build_vegeta_nc(n, text):
    if n == 1: return f"{text} 𝐓ᴇƦꞮ 𝐌ᴀᴀ 𝐊Ɪ 𝐂ʜᴜᴛ 𝐒ꞮʟᴀʏꞮ 𝐊Ʀ 𝐃ᴇɴɢᴇ 𝐇ᴜᴍ 𝐁ʜᴀꞮ " + _rep("𒈙👑", 18) + f"<{random.choice(VEGETA_EMOJI[0])}>"
    if n == 2: return f"{random.choice(VEGETA_EMOJI[1])} {text} 𝙇𝙐𝙉𝘿 𝘾𝙃⭕⭕𝙎𝙎 /- " + _rep("𒐫𒐫𒐫💚", 20) + "𒐫𒐫"
    if n == 3: return f"{text} 匚卄ㄩ卩 ᥅ꪖꪀᦔﺃᛕꫀ ᥇ꪖᥴᥴ𝙃ꫀ " + "".join(f"𒈙⸻{e}" for e in ["🩵","❤️","🩷","🧡","💛","💚","💙","💜","🖤","🩶","🤍","❣️"])
    if n == 4: return f"{text} 𝐏𝐈𝐋𝐋𝐄 😩 𝐒ᴀʏ 𝗩𝗘𝗚𝗘𝗧𝗔 𝐃ᴀᴅʏ 𓆩💗𓆪x " + _rep("𒀱ꪳ💝", 25)
    if n == 5: return f"{text}  ƇӇƲƤ ƦƝƊƖƘЄ " + _rep("𒈙⸻🐬", 20)
    if n == 6: return f"{text} PILLA 😭 SAY VEGETA BAGWAN {random.choice(VEGETA_EMOJI[2])}" + _rep("𒈙", 80)
    if n == 7: return f"{text} ༆𝐇𝟖𝐑 𝐑𝐀𝐍𝐃𝐀𝐋 𝐍𝐎𝐑𝐈𝐌𝐄 𝐂𝐕𝐑 𝐊𝐑,᭄⫸{random.choice(VEGETA_EMOJI[3])}⫷🔥🤟࿐" + _rep("𒐫", 60)
    if n == 8: return f"{text} 𓆃𒁃🖤" + _rep("𒁃🖤", 40)
    if n == 9: return f"{text} 𝗧ᴍᴋᴄ 〄💜꧅🩵〄🩷꧅❤️〄💛꧅🤎" + _rep("〄💜꧅🩵〄🩷꧅❤️〄💛꧅🤎", 20)
    if n == 10: return f"{text}  𓆩{random.choice(VEGETA_EMOJI[4])}𓆪" + _rep("█", 150) + " TMKC"
    return text

SPAM_EMOJI = {2: ["❤️","🧡","💛","💚","💙","💜","🖤"],
              3: ["❄️","🥶","🧊","🌨️","☃️","⛄","🌬️","💨","🌫️"]}

def build_spam(n, text):
    if n == 1:
        block = (f"#{text} #𝗚𝗔𝗡𝗗𝗠𝗔𝗥𝗘 𝗧𝗘𝗥𝗜 𝗜𝗧𝗡𝗜 𝗛𝗜𝗠𝗠𝗔𝗧 𝗧𝗨 "
                 f"#𝗟𝗨𝗙𝗙𝗬 𝗕𝗔𝗔𝗣 𝗞𝗘 𝗦𝗔𝗠𝗡𝗘 #𝗔𝗪𝗔𝗭 𝗨𝗖𝗛𝗜 𝗞𝗥𝗘𝗚𝗔 ?? "
                 f"𝗠𝗔𝗗𝗥𝗖𝗛⭕️𝗗 🤍🌙🕊️_____________________/ ")
        return block * 20
    if n == 2:
        return f"{text} Tᴇʀɪ Mᴀᴀ Kᴇ Bʜᴏsᴅᴇ Mᴇ 𝟼𝟺ɢʙ rᴅᴘ ᴅᴀʟᴅᴜ <{random.choice(SPAM_EMOJI[2])}>\n\n\n" * 15
    if n == 3:
        return f"#{text}  ᴛᴇʀɪ  ᴍᴀᴀ  ᴄʜᴏᴅ  ᴋᴇ  ᴍᴀᴀʀ  ᴅᴜɴɢᴀ  ᴋᴜᴛᴛɪᴋᴇ  /-----------------------------‐--------{random.choice(SPAM_EMOJI[3])} " * 25
    if n == 4:
        return (f"─── ⋆⋅☆⋅⋆ ──{text} 𝙈𝘼𝘿𝘼𝙍𝘾𝙃 ⭕ 𝘿─── ⋆⋅☆⋅⋆ ───"
                f"── ⋆⋅☆⋅⋆ ── 🩵 𝗨𝗧𝗛 𝗚𝗨𝗟𝗔𝗠 𝗠𝗔𝗥𝗔 𝗞𝗘𝗦𝗘 ─── ⋆⋅☆⋅⋆ ───") * 10
    if n == 5:
        ems = ["🖤","❤️","🩶","🤍","🧡","💛","💚","🩵","💙","💜","🤎","🩷","💘","💝","💖","💗","💓","💞","💕","💌","💟","♥️","❣️","❤️‍🩹","💔","❤️‍🔥","🫀"]
        return "\n".join(f"⋆⋅☆⋅ {text}  रंडी पुत्र  ({e}) ⋆⋅☆⋅⋆" for e in ems)
    return text

RR_REPLIES = [
    "{text} textᴇʀɪ Dᴀᴅɪ  ᴋ ᴄʜᴍᴜᴛ ᴍᴀɪ ᴛᴀɴɢ ᴀᴛᴋᴀ ᴅᴜɴɢᴀ ғɪʀ ᴛᴇʀʏ ᴅᴀᴅᴜ sᴜsᴜ ᴋᴀɪsᴀ ᴋʀᴇɢɪ😍?",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋ ᴄʜᴜᴛᴀᴅᴏ ᴍᴀɪ 𝐃ɪɴᴏsᴀᴜʀ ᴋɪ ᴘᴏᴛʏʏ😁",
    "{text} ᴍᴀᴊᴅᴜʀɪ ᴋʀᴇɢᴀ ɢᴀʀᴇᴇʙ ᴛᴇʀʏ ᴍᴍʏ ᴋɪ ᴛᴀɴɢ ᴜᴛʜᴀᴋᴇ👻 ᴄʜᴜᴛ ᴍᴀᴊ ғɪᴋᴀʀɪ ᴊᴀʟᴀ ᴅᴜɴɢᴀ🙈",
    "{text} ᴇᴋ ʙᴀᴀᴛ ʙᴛᴀᴜ ᴛᴇʀᴀ ᴘᴀᴘᴀ ᴛᴇʀʏ ᴍᴍʏ ᴋᴏ ᴍᴇʀsᴀ ᴄʜᴜᴅᴠᴀ ᴋʀ ɢʜᴀʀ ᴄʜᴀʟᴀᴛᴇ ᴇʏ🤣👻",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋ ᴄʜᴜᴛᴀᴅ ᴘᴀʀ ᴊᴏ ᴘʜᴜɴsɪ ʜᴀ ᴜsᴋᴏ👻 ʟᴀᴀᴛ ᴍᴀʀᴋᴀ ᴘʜᴏᴅ ᴅᴜ ᴄʏ?",
    "{text} textᴇʀʏ ᴍᴍʏ ᴋᴀ england ᴡᴀʟᴇ ʙᴜs ᴍᴀɪ ɢᴀɴɢ ʙᴀɴɢ ᴋʀᴋᴇ ᴋʜɪᴅᴋɪ sᴀ ғᴇᴋ ᴅᴇɴɢᴇ😭🥺",
    "{text} ᴋᴀʟɪ ᴋᴜᴛᴛɪ ᴋɪ ᴄʜᴜᴛ sᴀ ɴɪᴋʟᴀ ᴋᴜᴛᴛᴀ ᴋᴀ ᴘɪʟʟᴀ👻 ᴛᴇʀʏ ᴍᴀᴀ ʜᴀᴄᴋʟᴀ ᴋʀ ᴍᴀʀ ᴊᴀʏᴇ🤣",
    "{text} ᴊʜᴀᴛᴜ ᴛᴇʀʏ ᴀᴜᴋᴀᴛ ʜᴀ? 𝐋ᴜꜰꜰʏ  sE ʟᴀᴅɴᴇ ᴋɪ? tᴇʀʏ ᴍᴍʏ ᴋɪ ᴘᴜsʏʏ ᴘʀ ᴀʙᴅᴜʟ ᴋɪ ᴄʜᴀᴘᴀʟ ᴍᴀʀᴅᴜɴɢᴀ😁🍃",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋᴏ 𝐋ᴜꜰꜰʏ ᴋ ᴀʟᴀᴠᴀ ᴋᴏɪ ᴏʀ ᴄʜᴏᴅ sᴀᴋᴛᴀ ᴇʏ ᴋᴛᴀ?😁",
    "{text} sᴜᴀʀ ᴛᴇʀʏ ᴍᴍʏ ᴋɪ ᴄʜᴜᴛ ᴋᴀɪsᴀ ʟᴀᴀᴅᴋʜᴀᴅᴀɪ?👻 textᴇʀᴀ 𝐋ᴜꜰꜰʏ𖤍 Pᴀᴘᴀ ᴋᴀ ʟᴜɴ ᴅᴇᴋʜ ᴋʀ??😍",
    "{text} ᴛᴇʀɪ ᴅᴀᴅɪ ᴋᴀ ʙʜᴏsᴅᴀ ᴍᴀ 𝐒ʟᴀᴛᴇ ᴋɪ ᴍɪssɪʟᴇ ᴅᴀʟᴋᴇ ᴜᴅᴀ ᴅᴜɴɢᴀ😍",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋᴏ miya ᴋ sᴀᴛʜ ᴄʜᴏᴅᴇɢᴀᴀ🙈",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴊᴀʙ ᴛʀᴀɪɴ ᴍᴀɪ sᴏʏᴇɢɪ ᴛᴀʙ ᴜsᴋɪ ᴘᴀɴᴛʏ ᴜᴛᴀʀ ᴋʀ sᴜᴘ sᴜᴘ ᴋʀᴅᴜɴɢᴀ😍🦈🦈🦈",
    "{text} ᴛᴇʀʏ ᴅᴀᴅɪ ᴋ ᴄʜᴜᴛᴀᴅ ᴍᴀ ᴀᴀᴍ ᴋᴀ ᴛʀᴇᴇ ʟɢᴀᴋᴇ 𝐋ᴜɴ ғᴇᴋ ᴍʀ ᴍᴀʀᴋᴇ ᴛᴏʀᴜɴɢᴀ😘🤩",
    "{text} ᴛᴇʀɪ ᴍᴍʏ 𝐋ᴜꜰꜰʏ ᴋ ᴛᴀᴛᴛᴇ ᴋ ɴɪᴄʜᴇ 👻👻 ᴍᴀsʟɪ ɢʏɪ ᴀᴀʙ ᴛᴇʀᴀ ᴘᴀᴘᴀ ʀᴏʏᴇɢᴀ😘",
    "{text} ᴛᴇʀɪ ᴋᴀʟᴀ ᴄʜᴜᴛᴀᴅ ᴡᴀʟɪ ʙʜᴇɴ ᴋ ɢᴀɴᴅ ᴍᴀɪ👻 ᴊᴀᴅᴜɪ ᴄʜᴀᴅɪ ᴅᴀʟᴅᴜɴɢᴀ😈😈😈",
    "textERI BRHEN KI KALI BURR ME textHOOK DOYA AB CHAAtext JAA USE 👽",
    "{text} ᴋɪ ᴍᴀᴀ ʜᴏʀɴᴇʏ ʜᴏ ᴋʀ ᴀᴘɴᴇ ᴋᴜᴛᴛᴀ ᴋ ᴍᴜʜ ᴍᴀɪ ʟᴇ ʟᴇᴛɪ ᴇʏ?😱",
    "{text} ᴋɪ ᴍᴀᴀ ᴀᴅɪᴠᴀsɪ ᴏɪʟ ʟɢᴀᴋᴇ ᴊᴜɴɢʟᴇ ᴍᴀ ɢᴀɴᴅ ᴅᴇᴛɪ ᴇʏ😭😭",
    "{text} ᴋɪ ᴍᴍʏ 𝐋ᴜꜰꜰʏ ᴋᴀ ʟᴏʀᴀ ʟᴇᴛᴀ ʜᴜ ᴘᴀᴀᴅ ᴍᴀʀᴛɪ ᴇʏ ᴄʜɪ🤬🤬🤬",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ʙɪᴊʟɪ ᴋ ᴋʜᴀᴍʙᴀ ᴘʀ ᴡɪʀᴇ ᴄʜᴜᴛᴀᴅ ᴍᴀ ʟᴇᴋʀ ᴛᴀᴅᴀᴘ ᴋʀ ᴍᴀʀ ɢᴀɪ😭👻",
    "{text} ᴊɪs sɪᴍ sᴀ ᴛᴜ ɴᴇᴛ ᴄʜᴀʟᴀ ʀᴀʜᴀ ᴠᴏ ᴠ ᴍᴇʀᴀ ʟᴏᴅᴀ ᴋɪ ᴋʀɪᴘᴀ ʜᴀ ᴇʏ ɢᴀʀᴇᴇʙ ᴛᴇʀʏ ᴍᴀᴀ sᴀ ᴘᴜᴄʜ😁💣",
    "{text} ʜᴀᴄᴋʟᴇ ᴍssɢ ᴍᴛ ᴋʀ ᴡᴀʀɴᴀ ᴛᴇʀᴀ ᴋʜᴀɴᴅᴀɴ ᴋᴏ ʀᴀᴏᴅ ᴘʀ ɴᴀɴɢᴀ ᴋʀᴋʀ ᴍᴜʜ ᴘʀ ɢᴀʀᴀᴍ ᴍᴜᴛ ᴅᴜɴɢᴀ😍🦈",
    "{text} ᴋɪ ᴍᴀᴀ 𝐋ᴜꜰꜰʏ ᴋ ʟᴜɴ ᴋɪ ᴘʜᴏᴛᴏ ᴅᴇᴋʜ ᴋʀ ғɪɴɢᴇʀɪɴɢ ᴋʀᴛɪ ᴇʏ🦈😭",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋᴀʟᴀ ᴄʜᴜᴛᴀᴅ ᴡᴀʟɪ ᴄʜᴜᴅᴀᴋʀ😈💋",
    "{text} ᴋɪ ᴍᴜᴍᴍʏ ᴍᴜᴛʜɪ ᴍᴀʀ ᴛɪ ᴇʏ?😭????",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋ ᴄʜᴜᴛᴀᴅ 😘 ᴘʀ 𝐋ᴜꜰꜰʏ ᴀᴘɴᴀ ʟᴜɴ sᴀ ᴛᴀʟɪʏᴀ ʙᴀᴊᴀʏᴇɢᴀ😈😈💋",
    "{text} ᴋɪ ᴍᴜᴍᴍʏ ᴀᴘɴɪ ᴄʜᴜᴄʜɪʏᴀ ɢᴀᴛᴇ ᴋ ʙɪᴄʜ ᴅᴀʙᴀ ᴋʀ ᴍᴀʀ ɢᴀɪ?😭😭",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ʜɪᴢʀᴇ ʙᴀɴᴋʀ ᴛʀᴀɪɴ ᴍᴀ ᴀᴛɪ ᴛᴇʀᴀ ᴘᴀᴘᴀ sᴜsᴜ ᴄʜᴀᴛɴᴇ ᴋɪ ᴅᴜᴋᴀɴ ᴋʀᴛᴀ ᴇʏ ʙᴛᴀ ᴅʏ ᴄʏᴀ sᴀʙᴋᴏ👻👻👻💣💣",
    "ᴋʏᴀᴀ?😱 {text} ᴋɪ ᴍᴍʏ ᴊᴀʙ sᴜsᴜ ᴋʀ ʀɪ ᴛʜɪ textᴀʙ ᴄʜᴜᴛ ᴍᴀɪ sᴀᴀᴘ ɢʜᴜs ɢʏᴀ ᴠᴏ ʙʜɪ ᴄᴏʙʀᴀ?😱😱",
    "{text} ᴋɪ ʙᴇʜᴇɴ ᴋʜᴀᴅɪ ʜᴏ ᴋʀ ᴍᴜᴛ ᴛɪ ᴇʏ?😱😱😱",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋᴏ 𝐋ᴜꜰꜰʏ ɴᴀ ɴᴀsʜᴇ ᴍᴀɪ sᴏғᴀ ᴘʀ ᴛᴀɴɢ ᴜᴛʜᴀ ᴋʀ ᴄʜᴏᴅ ᴅɪʏᴀ😁😁",
    "{text} ᴛᴇʀɪ ᴍᴍʏ 𝐋ᴜꜰꜰʏ ᴋ ᴛᴀᴛᴛᴇ ᴋ ɴɪᴄʜᴇ 👻👻 ᴍᴀsʟɪ ɢʏɪ ᴀᴀʙ ᴛᴇʀᴀ ᴘᴀᴘᴀ ʀᴏʏᴇɢᴀ😘",
    "{text} ᴛᴇʀɪ ᴍᴀᴀ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ᴀᴀɢ ʟɢᴀ ᴋᴇ ʀᴀᴋʜ ᴅᴜɴɢᴀ🔥🥵",
    "{text} ᴛᴇʀᴀ ᴘᴀᴘᴀ ʀᴀɴᴅɪ ᴋʜᴀɴᴀ ᴍᴀ ɢᴀɴᴅ ᴍᴀʀ ᴋʀ ᴋᴀᴍᴀᴛᴀ ʜᴀ🩸💔",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ʀᴇᴅ ʟɪɢʜᴛ ᴍᴀ ᴄʜᴏᴅ ᴋᴇ ʙʜᴀɢᴀ ᴅᴜɴɢᴀ🚨🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ɢᴀɴᴅ ᴍᴇ sᴀᴘ ᴅᴀʟ ᴋᴇ ɴᴀᴄʜᴡᴀᴜɴɢᴀ🐍💃",
    "{text} ᴛᴇʀᴀ ᴘᴜʀᴀ ᴋʜᴀɴᴅᴀɴ ʀᴀɴᴅɪ ᴋʜᴀɴᴀ ᴍᴇ ɴᴀᴄʜᴛᴀ ʜᴀ🎭🍺",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ʟᴜғғʏ ᴋᴇ ʟᴜɴ sᴇ ɢᴀʀᴍɪ ᴅᴇᴛᴀ ʜᴜ🔥💦",
    "{text} ᴛᴇʀɪ ᴅᴀᴅɪ ʙʜᴇɴ ᴅᴏɴᴏ ᴋᴏ ᴇᴋ sᴀᴛʜ ᴄʜᴏᴅ ᴋᴇ ɴᴀᴄʜᴀᴜɴɢᴀ🎉🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ᴄʜᴜᴛ ᴋɪ ʜᴏᴛᴇʟ ᴋʜᴏʟ ᴋᴇ ʀᴀᴋʜ ᴅᴜɴɢᴀ🏨🩵",
    "{text} ᴛᴇʀᴀ ʙᴀᴀᴘ ᴄʜᴀᴜᴋɪᴅᴀʀ ʜᴀ textERI MAKI ɢᴀɴᴅ ᴋᴀ👻🚔",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ɢᴀɴɢ ʙᴀɴɢ ᴋʀᴋᴇ ᴛʀᴀɪɴ sᴇ ᴜᴛᴀʀᴡᴀᴜɴɢᴀ🚂🩸",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋɪ ɢᴀɴᴅ ᴍᴇ ʟᴜғғʏ ᴋᴀ ʟᴏɢᴏ ᴛᴀᴛᴛᴏᴏ ᴋᴀʀᴀ ᴅᴜɴɢᴀ🕸️🔱",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ᴛʀɪᴘʟᴇ x ᴠɪᴅᴇᴏ ʙᴀɴᴀᴋᴇ ᴠɪʀᴀʟ ᴋᴀʀ ᴅᴜɴɢᴀ📸🔥",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ᴅᴏɢɢʏ sᴛʏʟᴇ ᴍᴀ ᴄʜᴏᴅ ᴋᴇ ɴᴀᴄʜᴇ ɢɪʀᴀ ᴅᴜɴɢᴀ🐕🩸",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ʟᴜғғʏ ɢᴀɴɢ ᴋᴀ ʀᴀᴠᴀ ʟɢᴀ ᴅᴜɴɢᴀ🔊🩵",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ɢᴀɴᴅ ᴍᴀ ᴛᴀʟᴀʙ ᴋᴀ ᴘᴀɴɪ ʙʜᴀʀ ᴋᴇ ɴᴀᴄʜᴀᴜɴɢᴀ🌊🩸",
    "{text} ᴛᴇʀᴀ ᴘᴀᴘᴀ ʀᴀɴᴅɪ ᴋʜᴀɴᴀ ᴍᴀ ᴍᴜᴛ ᴋᴇ ʙᴇᴄʜ ᴅᴜɴɢᴀ🍺🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ɢᴀʏ sᴛʏʟᴇ ᴍᴀ ᴄʜᴏᴅ ᴋᴇ ᴠɪʀᴀʟ ᴋᴀʀ ᴅᴜɴɢᴀ📱🔥",
    "{text} ᴛᴇʀɪ ᴅᴀᴅɪ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ᴄᴏᴋᴇ sᴛᴜᴅɪᴏ ᴋʜᴏʟ ᴅᴜɴɢᴀ🥤🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ɢᴀɴᴅ ᴍᴀ sᴛᴀᴅɪᴜᴍ ᴍᴀ ᴍᴀᴛᴄʜ ᴋᴀʀᴀ ᴅᴜɴɢᴀ🏟️🩸",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ʟᴜғғʏ ɢᴀɴɢ ᴋᴀ ᴛᴀᴛᴛᴏᴏ ʙᴀɴᴡᴀ ᴅᴜɴɢᴀ🕸️🩵",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ᴘᴜʙʟɪᴄ ᴍᴀ ᴄʜᴏᴅ ᴋᴇ ᴠɪʀᴀʟ ᴋᴀʀ ᴅᴜɴɢᴀ📢🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ɢᴀɴᴅ ᴍᴀ ᴅᴇᴇᴘғᴀᴋᴇ ʙᴀɴᴀᴋᴇ ᴘᴏsᴛ ᴋᴀʀ ᴅᴜɴɢᴀ📸🔥",
    "{text} ᴛᴇʀᴇ ᴋʜᴀɴᴅᴀɴ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ᴅʀᴏɴᴇ ᴄᴀᴍᴇʀᴀ ʟᴀɢᴀ ᴅᴜɴɢᴀ🚁🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ʟᴜғғʏ ɢᴀɴɢ ᴋᴇ ʜᴀᴡᴀʟᴇ ᴋᴀʀ ᴅᴜɴɢᴀ🏴‍☠️🩸",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ʀᴀᴘ ʙᴀᴛᴛʟᴇ ᴋᴀʀᴡᴀ ᴅᴜɴɢᴀ🎤🩸",
]

PILLE_TEXT = "{user} 𝗕𝗛𝗔𝗡𝗚𝗜 𝗠𝗔𝗗𝗔𝗥𝗖𝗛⭕️𝗗 𓂃𓂃𓂃𓂃〉〈{emojie}〉〈𓂃𓂃𓂃𓂃𓂃𓂃..!¡"
PILLE_EMOJIS = ["❄️","🧊","🥶","🌨️","☃️","⛄","⛷️","🏂","⛸️","🏔️","🍧","🍨","🍦","🛷"]

CHUD_REPLIES = [
    "TERY MA RAND BTT KHTMM",
    "TERI MA KI KACCHI ME LAWDA MERA OK?",
    "AWW ACHA TMKC",
    "CHLNA TMKC TUJHE BHAWW DUN? HTT CHMR",
    "EK KAAM TU CHHA KRTA HAI AUR WO KAAM HAI LUFFY KA LAWDA SEHLANA 😉",
    "TERI MA NALI M CHODU",
    "MA KE LODE LUN TE VAJJ",
    "TMKC PE MUKKE MAARU",
    "ACHA RUNDYKE ?",
    "OYE GULAM CHUPP",
    "TMKC PE THOOK DIYA MENE ROO AB",
    "(MEHKA LADLE MEOWW) TMKC ME MUH DEKE YHI BOLUNGA 😉",
    "TERA REAL FATHER LUFFY",
    "TERI MAA KO NANGI KRKE BAZAR ME CHODU",
    "GAREEB MAA KI GREEB CHUT SE NIKLE HUE GAREEB LADKE AWAZ NICHE KRR 😂",
    "HURRRREE TERI MAA TO MARR GYI REHH",
    "CHUDEGA KYA REHHHH??",
    "JALDI TYPE KRR REE MAA K LUND",
    "TERI BEHEN K GALE PE PATTA BANDH KRR CHODU 😂",
    "KYA RE DALIT MADARCHOD HAWA ME UDEGA ?",
    "CHOTE ABHI TU ITNA BADA NHI HUA JO LUFFY K SAMNE AWAZ UCHI KREGA",
    "TMKC KO I LOVE UHH LUND SE 😂",
    "𝐂ʜʟ 𝐇ᴀʀᴍᴢᴀᴅ𝐈 𝐊ᴇ लड़के",
    "oi 𝐓ᴇʀɪ 𝐌‌ᴀᴀ गुलाम",
    "chl rndyce chud ke dikha",
    "TERI 𝐌ᴀᴀ 𝐌ᴀʀʀ 𝐆ᴀʏɪ naacho  !",
    "tera baap bass LUFFY hai 😂🎀",
    " CHUDAI FEEL KRR RUNDYKE",
    "ROO MTT TERI MAA ME HI CHODUNGA BSS KHUSH 😉",
]

HEARTRR = [
    "⤹𝀘🧡⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘🧡⤸",
    "⤹𝀘💛⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💛⤸",
    "⤹𝀘💚⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💚⤸",
    "⤹𝀘💙⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💙⤸",
    "⤹𝀘💜⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💜⤸",
    "⤹𝀘🖤⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘🖤⤸",
    "⤹𝀘🤍⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘🤍⤸",
    "⤹𝀘🤎⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘🤎⤸",
    "⤹𝀘💖⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💖⤸",
    "⤹𝀘💗⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💗⤸",
    "⤹𝀘💓⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💓⤸",
    "⤹𝀘💞⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💞⤸",
    "⤹𝀘💕⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💕⤸",
    "⤹𝀘💘⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💘⤸",
    "⤹𝀘💝⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💝⤸",
    "⤹𝀘💟⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💟⤸",
    "⤹𝀘❣️⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘❣️⤸",
    "⤹𝀘❤️‍🔥⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘❤️‍🔥⤸",
    "⤹𝀘❤️‍🩹⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘❤️‍🩹⤸",
]

FLAGRR = [
    " ོ༘₊⁺🇮🇳 ₊⁺⋆.˚ TERI MA KO INDIA ME CHODU  ོ༘₊⁺🇮🇳 ₊⁺⋆.˚",
    " ོ༘₊⁺🇯🇵 ₊⁺⋆.˚ TERI MA KO JAPAN ME CHODU ོ༘₊⁺🇯🇵 ₊⁺⋆. ",
    " ₊⁺🇺🇸 ₊⁺⋆.˚ TERI MA KO USA ME CHODU ོ༘₊⁺🇺🇸 ₊⁺⋆.˚",
    " ོ༘₊⁺🇬🇧 ₊⁺⋆.˚ TERI MA KO UK ME CHODU ོ༘₊⁺🇬🇧 ₊⁺⋆.˚",
    " ོ༘₊⁺🇰🇷 ₊⁺⋆.˚TERI MA KO KOREA ME CHODU ོ༘₊⁺🇰🇷 ₊⁺⋆.˚",
    " ོ༘₊⁺🇩🇪 ₊⁺⋆.˚ TERI MA KO GERMANY ME CHODU ོ༘₊⁺🇩🇪 ₊⁺⋆.˚",
    " ོ༘₊⁺🇫🇷 ₊⁺⋆.˚TERI MA KO FRANCE ME CHODU ོ༘₊⁺🇫🇷 ₊⁺⋆.˚",
    " ོ༘₊⁺🇮🇹 ₊⁺⋆.˚ TERI MA KO ITALY ME CHODU ོ༘₊⁺🇮🇹 ₊⁺⋆.˚",
    " ོ༘₊⁺🇧🇷 ₊⁺⋆.˚TERI MA KO BRAZIL ME CHODU ོ༘₊⁺🇧🇷 ₊⁺⋆.˚",
    " ོ༘₊⁺🇨🇦 ₊⁺⋆.˚TERI MA KO CANADA ME CHODU ོ༘₊⁺🇨🇦 ₊⁺⋆.˚",
]

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ 𝐀𝐃𝐃 𝐓𝐎𝐊𝐄𝐍 / 𝐁𝐎𝐓", callback_data="menu_addbot")],
        [InlineKeyboardButton("🏴‍☠️ 𝗟𝗨𝗙𝗙𝗬 𝗡𝗖", callback_data="menu_luffy"),
         InlineKeyboardButton("👑 𝗩𝗘𝗚𝗘𝗧𝗔 𝗡𝗖", callback_data="menu_vegeta")],
        [InlineKeyboardButton("💥 𝗦𝗣𝗔𝗠", callback_data="menu_spam"),
         InlineKeyboardButton("🔥 𝗥𝗔𝗜𝗗", callback_data="menu_raid")],
        [InlineKeyboardButton("⚙️ 𝗕𝗢𝗧 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦", callback_data="menu_botsettings"),
         InlineKeyboardButton("🎯 𝗧𝗔𝗥𝗚𝗘𝗧𝗦", callback_data="menu_targets")],
        [InlineKeyboardButton("🖼️ 𝗣𝗙𝗣 𝗟𝗢𝗢𝗣", callback_data="menu_pfp"),
         InlineKeyboardButton("🎮 𝗙𝗨𝗡", callback_data="menu_fun")],
        [InlineKeyboardButton("🛡️ 𝗚𝗥𝗢𝗨𝗣 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦", callback_data="menu_group"),
         InlineKeyboardButton("🛑 𝗦𝗧𝗢𝗣 𝗧𝗔𝗦𝗞", callback_data="menu_stop")],
        [InlineKeyboardButton("⚡ 𝗦𝗣𝗘𝗘𝗗 𝗖𝗢𝗡𝗧𝗥𝗢𝗟", callback_data="menu_speed")],
        [InlineKeyboardButton("✏️ 𝗘𝗗𝗜𝗧𝗦", callback_data="menu_edits")],
    ])

def back_button(target="menu_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data=target)]])

# ═══════════════════════════════════════════════════════════════════════
#   PER-BOT TURBO WORKERS
# ═══════════════════════════════════════════════════════════════════════

async def _per_bot_title_worker(bot_entry, chat_id, title_builder, stop_ref, interval):
    bot = bot_entry["bot"]
    bid = bot_entry["id"]
    while not stop_ref.get("stop"):
        if not _cooldown_ok(bid):
            await asyncio.sleep(0.05); continue
        try:
            title = title_builder()[:128]
            await asyncio.wait_for(bot.set_chat_title(chat_id, title), timeout=2.0)
            get_guard(bid)._successes += 1
        except RetryAfter as e: _set_cooldown(bid, float(e.retry_after))
        except asyncio.TimeoutError: _set_cooldown(bid, 2.0)
        except (Forbidden, BadRequest): pass
        except asyncio.CancelledError: raise
        except Exception: pass
        await asyncio.sleep(interval)

async def _per_bot_send_worker(bot_entry, chat_id, text_builder, stop_ref, interval, reply_to=None):
    bot = bot_entry["bot"]
    bid = bot_entry["id"]
    while not stop_ref.get("stop"):
        if not _cooldown_ok(bid):
            await asyncio.sleep(0.05); continue
        try:
            text = text_builder() if callable(text_builder) else text_builder
            await asyncio.wait_for(
                bot.send_message(chat_id, text, reply_to_message_id=reply_to), timeout=2.0)
        except RetryAfter as e: _set_cooldown(bid, float(e.retry_after))
        except asyncio.TimeoutError: _set_cooldown(bid, 2.0)
        except (Forbidden, BadRequest): pass
        except asyncio.CancelledError: raise
        except Exception: pass
        await asyncio.sleep(interval)

async def _per_bot_raid_worker(bot_entry, chat_id, reply_to, target_name, templates, react, stop_ref, interval):
    bot = bot_entry["bot"]
    bid = bot_entry["id"]
    while not stop_ref.get("stop"):
        if not _cooldown_ok(bid):
            await asyncio.sleep(0.05); continue
        try:
            tpl = random.choice(templates)
            txt = tpl.format(text=target_name)
            sent = await asyncio.wait_for(
                bot.send_message(chat_id, txt, reply_to_message_id=reply_to), timeout=2.0)
            if react and sent and HAS_REACTIONS:
                try:
                    await asyncio.wait_for(
                        bot.set_message_reaction(
                            chat_id=chat_id, message_id=sent.message_id,
                            reaction=[ReactionTypeEmoji(emoji="🤣")]), timeout=1.0)
                except: pass
        except RetryAfter as e: _set_cooldown(bid, float(e.retry_after))
        except asyncio.TimeoutError: _set_cooldown(bid, 2.0)
        except (Forbidden, BadRequest): pass
        except asyncio.CancelledError: raise
        except Exception: pass
        await asyncio.sleep(interval)

async def _per_bot_pfp_worker(bot_entry, chat_id, images, stop_ref, interval):
    bot = bot_entry["bot"]
    bid = bot_entry["id"]
    idx = random.randint(0, len(images) - 1) if images else 0
    while not stop_ref.get("stop"):
        if not _cooldown_ok(bid):
            await asyncio.sleep(0.05); continue
        try:
            img = images[idx % len(images)]
            await asyncio.wait_for(bot.set_chat_photo(chat_id=chat_id, photo=img), timeout=3.0)
            idx += 1
        except RetryAfter as e: _set_cooldown(bid, float(e.retry_after))
        except asyncio.TimeoutError: _set_cooldown(bid, 2.0)
        except (Forbidden, BadRequest): pass
        except asyncio.CancelledError: raise
        except Exception: pass
        await asyncio.sleep(interval)

# ═══════════════════════════════════════════════════════════════════════
#   MASTER HANDLERS
# ═══════════════════════════════════════════════════════════════════════

@only_sudo
async def start_cmd(update, context):
    t, fid = CFG["start_media_type"], CFG["start_media_file_id"]
    if t and fid:
        try:
            kw = {"caption": CFG["start_text"], "reply_markup": main_menu_kb()}
            if t == "photo": await update.message.reply_photo(photo=fid, **kw); return
            if t == "video": await update.message.reply_video(video=fid, **kw); return
            if t == "animation": await update.message.reply_animation(animation=fid, **kw); return
        except: pass
    await update.message.reply_text(CFG["start_text"], reply_markup=main_menu_kb(), parse_mode=ParseMode.MARKDOWN)

@only_owner
async def add_bot_cmd(update, context):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n`.add <TOKEN>`\n`.add <TOKEN1>,<TOKEN2>,<TOKEN3>`",
            parse_mode=ParseMode.MARKDOWN); return
    raw = " ".join(context.args)
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if not tokens:
        await update.message.reply_text("❌ No tokens found"); return
    status = await update.message.reply_text(f"⏳ Adding {len(tokens)} bot(s)...")
    results = []
    for tok in tokens:
        try:
            e = await CHILD_MGR.add_and_start(tok)
            tag = "already running" if e.get("_existed") else "started"
            results.append(f"✅ @{e['username']} (`{e['id']}`) — {tag}")
        except Exception as ex:
            short = tok[:20] + "..." if len(tok) > 20 else tok
            results.append(f"❌ `{short}` — {str(ex)[:80]}")
    try:
        await status.edit_text(
            f"*BOT ADD RESULTS ({len(tokens)}):*\n\n" + "\n".join(results) +
            f"\n\n*Total active:* `{len(all_bots())}`",
            parse_mode=ParseMode.MARKDOWN)
    except:
        await update.message.reply_text("\n".join(results))

@only_owner
async def del_bot_cmd(update, context):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n`.delbot <username>`\n`.delbot <username1>,<username2>`",
            parse_mode=ParseMode.MARKDOWN); return
    raw = " ".join(context.args)
    targets = [t.strip().lstrip("@") for t in raw.split(",") if t.strip()]
    results = []
    for t in targets:
        uname = await CHILD_MGR.stop_and_remove(t)
        if uname: results.append(f"✅ Removed @{uname}")
        else: results.append(f"❌ Not found: `{t}`")
    await update.message.reply_text("\n".join(results), parse_mode=ParseMode.MARKDOWN)

@only_owner
async def add_sudo_cmd(update, context):
    msg, uid = update.message, None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    elif context.args:
        try: uid = int(context.args[0])
        except: pass
    if not uid: await msg.reply_text("Reply to a user or `.ok <user_id>`"); return
    SUDO_USERS.add(uid); save_sudo()
    await msg.reply_text(f"✅ Added `{uid}` to sudo.", parse_mode=ParseMode.MARKDOWN)

@only_owner
async def del_sudo_cmd(update, context):
    msg, uid = update.message, None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    elif context.args:
        try: uid = int(context.args[0])
        except: pass
    if not uid: await msg.reply_text("Reply or `.delok <id>`"); return
    SUDO_USERS.discard(uid); save_sudo()
    await msg.reply_text(f"✅ Removed `{uid}` from sudo.", parse_mode=ParseMode.MARKDOWN)

@only_owner
async def list_sudo_cmd(update, context):
    if not SUDO_USERS: await update.message.reply_text("❌ No sudo users."); return
    await update.message.reply_text("👑 *𝐒𝐔𝐃𝐎*\n\n" + "\n".join(f"• `{u}`" for u in SUDO_USERS),
                                     parse_mode=ParseMode.MARKDOWN)

@only_owner
async def setstarttext_cmd(update, context):
    if not context.args:
        await update.message.reply_text(
            "Usage: `.setstarttext <new text>`\n"
            "Or reply to a message: `.setstarttext` (uses replied text)")
        return
    CFG["start_text"] = " ".join(context.args)
    save_config()
    await update.message.reply_text("✅ Start menu text updated.")

@only_owner
async def resetstart_cmd(update, context):
    CFG["start_text"] = DEFAULT_MENU_HEADER
    CFG["start_media_type"] = None
    CFG["start_media_file_id"] = None
    save_config()
    await update.message.reply_text("✅ Reverted to default branding.")

@only_owner
async def setstartmedia_cmd(update, context):
    r = update.effective_message.reply_to_message
    if not r: await update.message.reply_text("❌ Reply to a photo/video/animation."); return
    if r.video:
        CFG["start_media_type"] = "video"; CFG["start_media_file_id"] = r.video.file_id
    elif r.animation:
        CFG["start_media_type"] = "animation"; CFG["start_media_file_id"] = r.animation.file_id
    elif r.photo:
        CFG["start_media_type"] = "photo"; CFG["start_media_file_id"] = r.photo[-1].file_id
    else:
        await update.message.reply_text("❌ Unsupported."); return
    save_config()
    await update.message.reply_text(f"✅ Start media set as {CFG['start_media_type']}")

@only_owner
async def setgomedia_cmd(update, context):
    r = update.effective_message.reply_to_message
    if not r: await update.message.reply_text("❌ Reply to a photo/video/animation."); return
    if r.video:
        CFG["game_over_media"] = r.video.file_id; CFG["game_over_type"] = "video"
    elif r.animation:
        CFG["game_over_media"] = r.animation.file_id; CFG["game_over_type"] = "animation"
    elif r.photo:
        CFG["game_over_media"] = r.photo[-1].file_id; CFG["game_over_type"] = "photo"
    else:
        await update.message.reply_text("❌ Unsupported."); return
    save_config()
    await update.message.reply_text(f"✅ Game over media set as {CFG['game_over_type']}")

async def stop_task_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not context.args:
        await msg.reply_text("Usage: `.s <command_name>` or `.sall`"); return
    if not await claim_once(chat.id, "s", msg.message_id): return
    name = context.args[0].lower()
    n = _cancel_named(chat.id, name)
    if name == "slide":
        SLIDE_TRACKERS[chat.id] = []; n += 1
    await msg.reply_text(f"🛑 Stopped `{name}` ({n} tasks)")

async def stop_all_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "sall", msg.message_id): return
    total = 0
    for cid in list(NAMED_TASKS.keys()):
        total += _cancel_all_named(cid)
    ACTIVE_TASKS.clear(); SLIDE_TRACKERS.clear()
    await msg.reply_text(f"🛑🛑 ALL TASKS STOPPED ({total})")

@only_sudo
async def speed_cmd(update, context):
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "speed", msg.message_id): return
    if len(context.args) < 2:
        await msg.reply_text(
            "⚡ *SPEED CONTROL*\n\n"
            "Usage: `.speed <cat> <seconds>`\n"
            "Categories: `nc`, `spam`, `raid`, `pfp`, `slide`, `all`\n\n"
            "Example: `.speed all 0.01` (turbo)\n"
            "Default: nc=0.1, spam=0.02, raid=0.05, pfp=0.1",
            parse_mode=ParseMode.MARKDOWN); return
    key = context.args[0].lower()
    try: val = max(0.0, float(context.args[1]))
    except: await msg.reply_text("❌ Invalid seconds"); return
    if key not in list(DEFAULT_INTERVALS.keys()) + ["all"]:
        await msg.reply_text("❌ Invalid category"); return
    set_interval(chat.id, key, val)
    await msg.reply_text(f"⚡ Speed: `{key}` = `{val}s`", parse_mode=ParseMode.MARKDOWN)

@only_owner
async def gameover_cmd(update, context):
    msg, chat = update.effective_message, update.effective_chat
    if not msg or not chat: return
    if not await claim_once(chat.id, "dfn", msg.message_id): return
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    user = update.effective_user
    name = f"@{user.username}" if user and user.username else (user.first_name if user else "UNKNOWN")
    gn = chat.title if chat.title else "UNKNOWN GROUP"
    text = (f"═════════════════════════\n"
            f"Ꮐᴀᴍᴇ ꪮᴠᴇʀ Ͳɪᴍᴇ - {now.strftime('%I:%M:%S %p')}\n"
            f"Ꭰᴀᴛᴇ - {now.strftime('%d %B %Y')} (IST)\n\n"
            f"Ꭺʙʙ Ᏼᴀᴀᴘ Ꮶᴇ Ꭺɢɢᴇ\nᎻᴀᴡᴀʙᴀᴢᴢɪ Ꮶᴀʀɴᴇ Ꮇᴛᴛ Ꭺɴᴀᴀ\n\n"
            f"Ꮐʀᴏᴜᴘ - {gn}\n\nͲᴇʀɪ Ꮇᴀᴀ Ꮯʜᴜᴅ Ꮶᴇ Ꭰꜰɴ Ᏼʏ - {name}\n"
            f"═════════════════════════")
    try: await msg.reply_video(video=CFG["game_over_media"], caption=text)
    except:
        try: await msg.reply_animation(animation=CFG["game_over_media"], caption=text)
        except:
            try: await msg.reply_photo(photo=CFG["game_over_media"], caption=text)
            except: pass

@only_sudo
async def set_target_cmd(update, context):
    msg, chat = update.effective_message, update.effective_chat
    if not msg or not chat: return
    if not await claim_once(chat.id, "settarget", msg.message_id): return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user with `.settarget <label>`"); return
    if not context.args:
        await msg.reply_text("Usage: `.settarget <label>`"); return
    label, uid = context.args[0].lower(), msg.reply_to_message.from_user.id
    TARGETS[uid] = label; TARGETS_REV[uid] = uid; save_targets()
    await msg.reply_text(f"✅ Set target `{label}` → `{uid}`", parse_mode=ParseMode.MARKDOWN)

@only_sudo
async def del_target_cmd(update, context):
    msg, chat = update.effective_message, update.effective_chat
    if not msg or not chat: return
    if not await claim_once(chat.id, "deltarget", msg.message_id): return
    uid = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    elif context.args:
        try: uid = int(context.args[0])
        except: pass
    if not uid or uid not in TARGETS:
        await msg.reply_text("❌ Target not found."); return
    del TARGETS[uid]; TARGETS_REV.pop(uid, None); save_targets()
    await msg.reply_text(f"✅ Removed target `{uid}`", parse_mode=ParseMode.MARKDOWN)

# ═══════════════════════════════════════════════════════════════════════
#   NC HANDLERS
# ═══════════════════════════════════════════════════════════════════════

async def _nc_handler(update, context, kind):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await msg.reply_text("❌ Use this in a group."); return
    if not context.args:
        await msg.reply_text(f"Usage: `.{kind}nc{{1-10}} <text>`", parse_mode=ParseMode.MARKDOWN); return
    cmd = msg.text.split()[0].split("@")[0].lstrip(".")
    m = re.match(rf"{kind}nc(\d+)$", cmd)
    if not m: return
    n = int(m.group(1))
    if not (1 <= n <= 10):
        await msg.reply_text("❌ Number must be 1-10"); return
    text = await _resolve_target(chat.id, context.bot, context.args)
    if not text and msg.reply_to_message and msg.reply_to_message.from_user:
        tu = msg.reply_to_message.from_user
        text = f"@{tu.username}" if tu.username else tu.first_name
    bots = all_bots()
    if not bots:
        await msg.reply_text("❌ No child bots added. Use `.add <token>` on master."); return
    interval = get_interval(chat.id, "nc")
    stop_ref = {"stop": False}
    def title_builder():
        t = build_luffy_nc(n, text) if kind == "luffy" else build_vegeta_nc(n, text)
        return t + random.choice(INVIS_SUFFIXES)
    def factory():
        return [asyncio.create_task(
            _per_bot_title_worker(b, chat.id, title_builder, stop_ref, interval)
        ) for b in bots]
    if not await claim_and_start_multi(chat.id, cmd, msg.message_id, factory):
        return
    ACTIVE_TASKS[chat.id] = cmd
    try:
        await msg.reply_text(
            f"⚡ 𝐍𝐂 {n} CORE — {len(bots)} bots × interval `{interval}s` "
            f"(runs until `.s {cmd}` or `.sall`)",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def luffy_nc_cmd(update, context): await _nc_handler(update, context, "luffy")
async def vegeta_nc_cmd(update, context): await _nc_handler(update, context, "vegeta")

async def spam_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await msg.reply_text("❌ Use in a group."); return
    if not context.args:
        await msg.reply_text("Usage: `.spam<1-5> <text>`", parse_mode=ParseMode.MARKDOWN); return
    cmd = msg.text.split()[0].split("@")[0].lstrip(".")
    m = re.match(r"spam(\d+)$", cmd)
    if not m: return
    n = int(m.group(1))
    if not (1 <= n <= 5):
        await msg.reply_text("❌ Must be 1-5"); return
    body = build_spam(n, " ".join(context.args))
    bots = all_bots()
    if not bots:
        await msg.reply_text("❌ No child bots."); return
    interval = get_interval(chat.id, "spam")
    stop_ref = {"stop": False}
    def factory():
        return [asyncio.create_task(
            _per_bot_send_worker(b, chat.id, body, stop_ref, interval)
        ) for b in bots]
    if not await claim_and_start_multi(chat.id, cmd, msg.message_id, factory):
        return
    ACTIVE_TASKS[chat.id] = cmd
    try: await msg.reply_text(f"⚡ 𝐒𝐏𝐀𝐌 {n} CORE — {len(bots)} bots.")
    except: pass

async def _raid_generic(update, context, key, templates, react):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    target_user, target_msg_id = None, None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
        target_msg_id = msg.reply_to_message.message_id
    elif context.args:
        uid = _label_to_uid(context.args[0])
        if uid:
            try:
                target_user = (await context.bot.get_chat_member(chat.id, uid)).user
                target_msg_id = msg.message_id
            except: pass
    if not target_user:
        await msg.reply_text(f"❌ Reply to a user or `.settarget` a label, then `.{key} t1`",
                             parse_mode=ParseMode.MARKDOWN); return
    target_name = f"@{target_user.username}" if target_user.username else target_user.first_name
    bots = all_bots()
    if not bots:
        await msg.reply_text("❌ No child bots."); return
    interval = get_interval(chat.id, "raid")
    stop_ref = {"stop": False}
    def factory():
        return [asyncio.create_task(
            _per_bot_raid_worker(b, chat.id, target_msg_id, target_name,
                                  templates, react, stop_ref, interval)
        ) for b in bots]
    if not await claim_and_start_multi(chat.id, key, msg.message_id, factory):
        return
    ACTIVE_TASKS[chat.id] = key
    await msg.reply_text(f"⚡ *{key.upper()}* CORE on `{len(bots)}` bots",
                         parse_mode=ParseMode.MARKDOWN)

async def rr_cmd(update, context): await _raid_generic(update, context, "rr", RR_REPLIES, True)
async def chud_cmd(update, context): await _raid_generic(update, context, "chud", CHUD_REPLIES, False)
async def heartrr_cmd(update, context): await _raid_generic(update, context, "heartrr", HEARTRR, False)
async def flagrr_cmd(update, context): await _raid_generic(update, context, "flagrr", FLAGRR, False)

async def pille_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user."); return
    target_user = msg.reply_to_message.from_user
    target_msg_id = msg.reply_to_message.message_id
    bots = all_bots()
    if not bots: await msg.reply_text("❌ No child bots."); return
    def _build():
        return PILLE_TEXT.format(user=target_user.first_name or "user",
                                  emojie=random.choice(PILLE_EMOJIS))
    interval = get_interval(chat.id, "raid")
    stop_ref = {"stop": False}
    def factory():
        return [asyncio.create_task(
            _per_bot_send_worker(b, chat.id, _build, stop_ref, interval, reply_to=target_msg_id)
        ) for b in bots]
    if not await claim_and_start_multi(chat.id, "pille", msg.message_id, factory):
        return
    ACTIVE_TASKS[chat.id] = "pille"
    await msg.reply_text("⚡ 𝐏𝐈𝐋𝐋𝐄 CORE 𝐒𝐓𝐀𝐑𝐓𝐄𝐃")

async def slide_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    target_user = None
    args = list(context.args)
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    elif args and _label_to_uid(args[0]):
        uid = _label_to_uid(args.pop(0))
        target_user = type("U", (), {"id": uid, "username": None, "first_name": str(uid)})()
    if not target_user:
        await msg.reply_text("❌ Reply to a user or `.slide t1 <text>`"); return
    if not args:
        await msg.reply_text("Usage: `.slide <text>`"); return
    text = " ".join(args)
    if not await claim_once(chat.id, "slide", msg.message_id):
        return
    SLIDE_TRACKERS[chat.id].append({
        "uid": target_user.id, "text": text, "owner_bot_id": context.bot.id,
    })
    ACTIVE_TASKS[chat.id] = "slide"
    await msg.reply_text(f"⚡ Sliding `{target_user.id}` with: `{text}`",
                         parse_mode=ParseMode.MARKDOWN)

async def slide_message_handler(update, context):
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not chat or not user: return
    if msg.text and msg.text.startswith("."): return
    trackers = SLIDE_TRACKERS.get(chat.id, [])
    if not trackers: return
    for tr in list(trackers):
        if tr["uid"] == user.id:
            if context.bot.id != tr["owner_bot_id"]: continue
            await safe_call(context.bot.send_message, chat.id, tr["text"],
                            reply_to_message_id=msg.message_id,
                            bot_id=context.bot.id, timeout=1.0)

# ═══════════════════════════════════════════════════════════════════════
#   GROUP MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

async def lock_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not await claim_once(chat.id, "lock", update.effective_message.message_id): return
    perms = ChatPermissions(can_send_messages=False)
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].set_chat_permissions, chat.id, perms, bot_id=b["id"], timeout=3.0)
            n += 1
        except: pass
    await update.message.reply_text(f"🔒 Group locked. {n} bots applied.")

async def unlock_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not await claim_once(chat.id, "unlock", update.effective_message.message_id): return
    perms = ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                            can_send_polls=True, can_send_other_messages=True,
                            can_add_web_page_previews=True, can_change_info=True,
                            can_invite_users=True, can_pin_messages=True)
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].set_chat_permissions, chat.id, perms, bot_id=b["id"], timeout=3.0)
            n += 1
        except: pass
    await update.message.reply_text(f"🔓 Group unlocked. {n} bots applied.")

async def promote_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user."); return
    if not await claim_once(chat.id, "promote", msg.message_id): return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].promote_chat_member, chat.id, uid,
                bot_id=b["id"], timeout=3.0,
                can_change_info=True, can_delete_messages=True, can_invite_users=True,
                can_restrict_members=True, can_pin_messages=True, can_promote_members=True,
                can_manage_video_chats=True, can_manage_chat=True)
            n += 1
        except: pass
    await msg.reply_text(f"⬆️ Promoted `{uid}` using {n} bots.", parse_mode=ParseMode.MARKDOWN)

async def demote_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user."); return
    if not await claim_once(chat.id, "demote", msg.message_id): return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].promote_chat_member, chat.id, uid,
                bot_id=b["id"], timeout=3.0,
                can_change_info=False, can_delete_messages=False, can_invite_users=False,
                can_restrict_members=False, can_pin_messages=False, can_promote_members=False,
                can_manage_video_chats=False, can_manage_chat=False)
            n += 1
        except: pass
    await msg.reply_text(f"⬇️ Demoted `{uid}` using {n} bots.", parse_mode=ParseMode.MARKDOWN)

async def admin_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not await claim_once(chat.id, "admin", msg.message_id): return
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].promote_chat_member, chat.id, b["id"],
                bot_id=b["id"], timeout=3.0,
                can_change_info=True, can_delete_messages=True, can_invite_users=True,
                can_restrict_members=True, can_pin_messages=True, can_promote_members=True,
                can_manage_video_chats=True, can_manage_chat=True)
            n += 1
        except: pass
    await msg.reply_text(f"👑 Admin ({n}/{len(all_bots())})")

async def mute_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user."); return
    if not await claim_once(chat.id, "mute", msg.message_id): return
    uid = msg.reply_to_message.from_user.id
    perms = ChatPermissions(can_send_messages=False)
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].restrict_chat_member, chat.id, uid, perms, bot_id=b["id"], timeout=3.0)
            n += 1
        except: pass
    await msg.reply_text(f"🔇 Muted `{uid}` ({n} bots)")

async def unmute_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user."); return
    if not await claim_once(chat.id, "unmute", msg.message_id): return
    uid = msg.reply_to_message.from_user.id
    perms = ChatPermissions(can_send_messages=True, can_send_media_messages=True,
        can_send_polls=True, can_send_other_messages=True,
        can_add_web_page_previews=True, can_invite_users=True)
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].restrict_chat_member, chat.id, uid, perms, bot_id=b["id"], timeout=3.0)
            n += 1
        except: pass
    await msg.reply_text(f"🔊 Unmuted `{uid}` ({n} bots)")

async def kick_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user."); return
    if not await claim_once(chat.id, "kick", msg.message_id): return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].ban_chat_member, chat.id, uid, bot_id=b["id"], timeout=3.0)
            await safe_call(b["bot"].unban_chat_member, chat.id, uid, bot_id=b["id"], timeout=3.0)
            n += 1
        except: pass
    await msg.reply_text(f"👢 Kicked `{uid}` ({n} bots)")

async def ban_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user."); return
    if not await claim_once(chat.id, "ban", msg.message_id): return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].ban_chat_member, chat.id, uid, bot_id=b["id"], timeout=3.0)
            n += 1
        except: pass
    await msg.reply_text(f"🚫 Banned `{uid}` ({n} bots)")

async def unban_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id):
        await update.message.reply_text(AUTHORIZATION_MSG); return
    msg, chat = update.effective_message, update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"): return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user."); return
    if not await claim_once(chat.id, "unban", msg.message_id): return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].unban_chat_member, chat.id, uid, bot_id=b["id"], timeout=3.0)
            n += 1
        except: pass
    await msg.reply_text(f"✅ Unbanned `{uid}` ({n} bots)")

# ═══════════════════════════════════════════════════════════════════════
#   FUN
# ═══════════════════════════════════════════════════════════════════════

async def cat_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "cat", msg.message_id): return
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.thecatapi.com/v1/images/search") as r:
                url = (await r.json())[0]["url"]
        await msg.reply_photo(url)
    except Exception as e: await msg.reply_text(f"❌ {e}")

async def dog_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "dog", msg.message_id): return
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://dog.ceo/api/breeds/image/random") as r:
                url = (await r.json())["message"]
        await msg.reply_photo(url)
    except Exception as e: await msg.reply_text(f"❌ {e}")

async def dice_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "dice", msg.message_id): return
    await msg.reply_dice(emoji="🎲")

async def quotes_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "quotes", msg.message_id): return
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://zenquotes.io/api/random") as r:
                q = (await r.json())[0]
        await msg.reply_text(f"💭 \"{q['q']}\"\n\n— *{q['a']}*", parse_mode=ParseMode.MARKDOWN)
    except Exception as e: await msg.reply_text(f"❌ {e}")

async def jokes_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "jokes", msg.message_id): return
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://official-joke-api.appspot.com/random_joke") as r:
                d = await r.json()
        await msg.reply_text(f"😂 {d['setup']}\n\n{d['punchline']}")
    except Exception as e: await msg.reply_text(f"❌ {e}")

async def ai_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "ai", msg.message_id): return
    if not context.args: await msg.reply_text("Usage: `.ai <prompt>`"); return
    prompt = " ".join(context.args)
    status = await msg.reply_text("🎨 *Generating...* 0%", parse_mode=ParseMode.MARKDOWN)
    try:
        for pct in [25, 50, 75]:
            await asyncio.sleep(0.4)
            try: await status.edit_text(f"🎨 *Generating...* {pct}%", parse_mode=ParseMode.MARKDOWN)
            except: pass
        url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1024&height=1024&nologo=true"
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r: data = await r.read()
        await status.delete()
        await msg.reply_photo(photo=data, caption=f"🎨 *{prompt}*", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        try: await status.edit_text(f"❌ {e}")
        except: pass

async def find_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "find", msg.message_id): return
    if not context.args: await msg.reply_text("Usage: `.find <music>`"); return
    q = " ".join(context.args)
    try:
        url = f"https://itunes.apple.com/search?term={quote(q)}&media=music&limit=3"
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r: data = await r.json()
        results = data.get("results", [])
        if results:
            lines = [f"🎵 *{q}*", ""]
            for r0 in results[:3]:
                lines.append(f"• *{r0.get('trackName','?')}* — {r0.get('artistName','?')}\n  {r0.get('trackViewUrl','')}")
            txt = "\n".join(lines)
        else: txt = f"🎵 Found: `{q}`"
        await msg.reply_text(txt, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    except Exception as e: await msg.reply_text(f"❌ {e}")

async def play_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "play", msg.message_id): return
    if not context.args: await msg.reply_text("Usage: `.play <song>`"); return
    await msg.reply_text(
        f"🎵 *Searching:* {' '.join(context.args)}\n\n"
        f"⚠️ Voice chat streaming requires PyTgCalls installed.",
        parse_mode=ParseMode.MARKDOWN)

# ═══════════════════════════════════════════════════════════════════════
#   PFP
# ═══════════════════════════════════════════════════════════════════════

async def savepfp_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "savepfp", msg.message_id): return
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.reply_text("❌ Reply to a photo with `.savepfp`"); return
    PFP_IMAGES[chat.id].append(msg.reply_to_message.photo[-1].file_id)
    save_pfp()
    await msg.reply_text(f"✅ Saved pfp #{len(PFP_IMAGES[chat.id])}")

async def allpfp_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "allpfp", msg.message_id): return
    imgs = PFP_IMAGES.get(chat.id, [])
    if not imgs: await msg.reply_text("❌ No pfps saved."); return
    img = imgs[0]
    coros = [safe_call(b["bot"].set_chat_photo, chat.id, photo=img, bot_id=b["id"], timeout=2.0)
             for b in all_bots()]
    results = await asyncio.gather(*coros, return_exceptions=True)
    n = sum(1 for r in results if r is not None and not isinstance(r, Exception))
    await msg.reply_text(f"✅ Set pfp on {n}/{len(all_bots())} bots")

async def pfplock_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "pfplock", msg.message_id): return
    PFP_LOOP_STATE[chat.id] = False; save_pfp()
    n = _cancel_named(chat.id, "pfploop")
    await msg.reply_text(f"🔒 PFP locked ({n} tasks).")

async def pfploop_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    chat = update.effective_chat
    if not chat: return
    imgs = PFP_IMAGES.get(chat.id, [])
    if not imgs: await update.message.reply_text("❌ No pfps saved. Use `.savepfp`."); return
    bots = all_bots()
    if not bots: await update.message.reply_text("❌ No child bots."); return
    PFP_LOOP_STATE[chat.id] = True; save_pfp()
    interval = get_interval(chat.id, "pfp")
    stop_ref = {"stop": False}
    def factory():
        return [asyncio.create_task(
            _per_bot_pfp_worker(b, chat.id, imgs, stop_ref, interval)
        ) for b in bots]
    if not await claim_and_start_multi(chat.id, "pfploop", update.effective_message.message_id, factory):
        return
    await update.message.reply_text(f"⚡ PFP TURBO LOOP started (interval {interval}s).")

async def deletepfp_cmd(update, context):
    if not update.effective_user or not is_authorized(update.effective_user.id): return
    msg, chat = update.effective_message, update.effective_chat
    if not chat: return
    if not await claim_once(chat.id, "deletepfp", msg.message_id): return
    PFP_IMAGES[chat.id] = []; PFP_LOOP_STATE[chat.id] = False; save_pfp()
    await msg.reply_text("🗑️ All saved pfps deleted.")

# ═══════════════════════════════════════════════════════════════════════
#   CALLBACK ROUTER
# ═══════════════════════════════════════════════════════════════════════

@only_sudo
async def callback_router(update, context):
    q = update.callback_query
    if not q: return
    data = q.data or ""
    answered = {"v": False}
    async def ans(text=None, alert=False):
        if answered["v"]: return
        try: await q.answer(text=text, show_alert=alert)
        except Exception: pass
        answered["v"] = True

    try:
        if data == "menu_main":
            await safe_edit(q, CFG["start_text"], reply_markup=main_menu_kb()); return
        if data == "menu_addbot":
            await safe_edit(q,
                "📥 *𝐀𝐃𝐃 𝐓𝐎𝐊𝐄𝐍 / 𝐁𝐎𝐓*\n\n"
                "Send the bot token as a message.\n"
                "Format: `.add <TOKEN>` — or bulk: `.add <TOKEN1>,<TOKEN2>,<TOKEN3>`\n\n"
                "Example:\n`.add 123456:ABCDEF...`\n\n"
                "You can add *unlimited* bots.",
                reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_luffy":
            kb = [[InlineKeyboardButton(f".luffync{i}", callback_data=f"cmd_luffync_{i}")
                   for i in range(j, min(j+5, 11))] for j in (1, 6)]
            kb.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")])
            await safe_edit(q,
                "🏴‍☠️ *𝐋𝐔𝐅𝐅𝐘 𝐍𝐂 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\n"
                "Usage: `.luffync<1-10> <text>`\nExample: `.luffync1 gali de`",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_vegeta":
            kb = [[InlineKeyboardButton(f".vegetanc{i}", callback_data=f"cmd_vegetanc_{i}")
                   for i in range(j, min(j+5, 11))] for j in (1, 6)]
            kb.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")])
            await safe_edit(q,
                "👑 *𝐕𝐄𝐆𝐄𝐓𝐀 𝐍𝐂 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\nUsage: `.vegetanc<1-10> <text>`",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_spam":
            kb = [[InlineKeyboardButton(f".spam{i}", callback_data=f"cmd_spam_{i}")
                   for i in range(j, min(j+3, 6))] for j in (1, 4)]
            kb.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")])
            await safe_edit(q,
                "💥 *𝐒𝐏𝐀𝐌 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\nUsage: `.spam<1-5> <text>`",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_raid":
            kb = [
                [InlineKeyboardButton(".rr", callback_data="menu_raid_rr"),
                 InlineKeyboardButton(".chud", callback_data="menu_raid_chud")],
                [InlineKeyboardButton(".heartrr", callback_data="menu_raid_heart"),
                 InlineKeyboardButton(".flagrr", callback_data="menu_raid_flag")],
                [InlineKeyboardButton(".pille", callback_data="menu_raid_pille"),
                 InlineKeyboardButton(".slide", callback_data="menu_raid_slide")],
                [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
            ]
            await safe_edit(q,
                "🔥 *𝐑𝐀𝐈𝐃 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\nReply to a user with the command.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data.startswith("menu_raid_"):
            key = data.replace("menu_raid_", "")
            mp = {"rr": ".rr", "chud": ".chud", "heart": ".heartrr", "flag": ".flagrr",
                  "pille": ".pille", "slide": ".slide <text>"}
            cmd = mp.get(key, f".{key}")
            await safe_edit(q,
                f"🔥 *{cmd}*\n\nReply to a user with `{cmd.split()[0]}`.",
                reply_markup=back_button("menu_raid"), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_botsettings":
            kb = [
                [InlineKeyboardButton("📊 𝗕𝗢𝗧 𝗦𝗧𝗔𝗧𝗨𝗦", callback_data="bs_status")],
                [InlineKeyboardButton("🤖 𝗔𝗟𝗟 𝗕𝗢𝗧𝗦", callback_data="bs_bots")],
                [InlineKeyboardButton("⏱️ 𝗗𝗘𝗟𝗔𝗬 𝗣𝗘𝗥 𝗕𝗢𝗧", callback_data="bs_delay")],
                [InlineKeyboardButton("🏓 𝗣𝗜𝗡𝗚", callback_data="bs_ping")],
                [InlineKeyboardButton("🔄 𝗥𝗘𝗙𝗥𝗘𝗦𝗛 𝗟𝗔𝗧𝗘𝗡𝗖𝗬", callback_data="bs_refresh")],
                [InlineKeyboardButton("🧠 𝗣𝗥𝗢𝗖𝗘𝗦𝗦𝗢𝗥", callback_data="bs_proc")],
                [InlineKeyboardButton("💻 𝗖𝗣𝗨", callback_data="bs_cpu")],
                [InlineKeyboardButton("📈 𝗣𝗘𝗥𝗙𝗢𝗥𝗠𝗔𝗡𝗖𝗘", callback_data="bs_perf")],
                [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
            ]
            await safe_edit(q, "⚙️ *𝐁𝐎𝐓 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒*",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data == "bs_status":
            lines = ["🟢 *𝐁𝐎𝐓 𝐒𝐓𝐀𝐓𝐔𝐒*", ""]
            for b in all_bots():
                st = get_guard(b["id"]).stats()
                cd = max(0, _bot_cooldown.get(b["id"], 0) - time.monotonic())
                cd_str = f" | cool {cd:.1f}s" if cd > 0 else ""
                lines.append(f"• @{b['username']} — fail={st['failures']}{cd_str}")
            if not all_bots(): lines.append("❌ No child bots.")
            await safe_edit(q, "\n".join(lines),
                reply_markup=back_button("menu_botsettings"), parse_mode=ParseMode.MARKDOWN); return
        if data == "bs_bots":
            lines = [f"🤖 *𝐀𝐋𝐋 𝐁𝐎𝐓𝐒* ({len(all_bots())})", ""]
            for b in all_bots():
                lines.append(f"• @{b['username']} (`{b['id']}`)")
            if not all_bots(): lines.append("❌ No child bots.")
            await safe_edit(q, "\n".join(lines),
                reply_markup=back_button("menu_botsettings"), parse_mode=ParseMode.MARKDOWN); return
        if data == "bs_delay":
            lines = ["⏱️ *𝐃𝐄𝐋𝐀𝐘 𝐏𝐄𝐑 𝐁𝐎𝐓*", ""]
            for b in all_bots(): lines.append(f"• @{b['username']}: {get_guard(b['id']).delay:.2f}s")
            if not all_bots(): lines.append("❌ No bots.")
            await safe_edit(q, "\n".join(lines),
                reply_markup=back_button("menu_botsettings"), parse_mode=ParseMode.MARKDOWN); return
        if data == "bs_ping":
            t0 = time.time()
            await safe_edit(q, "🏓 Pinging...", reply_markup=back_button("menu_botsettings"))
            ms = (time.time() - t0) * 1000
            await safe_edit(q, f"🏓 *𝐏𝐈𝐍𝐆:* `{ms:.2f} ms`",
                reply_markup=back_button("menu_botsettings"), parse_mode=ParseMode.MARKDOWN); return
        if data == "bs_refresh":
            for b in all_bots():
                try: await b["bot"].get_me()
                except: pass
            await safe_edit(q, "🔄 Refreshed.", reply_markup=back_button("menu_botsettings")); return
        if data == "bs_proc":
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            await safe_edit(q,
                f"🧠 *𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐎𝐑*\n\n"
                f"• Cores: `{psutil.cpu_count()}`\n• Usage: `{cpu:.1f}%`\n"
                f"• RAM: `{mem.percent:.1f}%` ({mem.used//1024//1024}MB / {mem.total//1024//1024}MB)",
                reply_markup=back_button("menu_botsettings"), parse_mode=ParseMode.MARKDOWN); return
        if data == "bs_cpu":
            cpu = psutil.cpu_percent(interval=None, percpu=True)
            txt = "💻 *𝐂𝐏𝐔*\n\n" + "\n".join(f"• Core {i+1}: `{c:.1f}%`" for i, c in enumerate(cpu))
            await safe_edit(q, txt, reply_markup=back_button("menu_botsettings"), parse_mode=ParseMode.MARKDOWN); return
        if data == "bs_perf":
            ts = tf = 0
            for b in all_bots():
                s = get_guard(b["id"]).stats()
                ts += s["successes"]; tf += s["failures"]
            pct = (ts / (ts + tf) * 100) if (ts + tf) else 100
            await safe_edit(q,
                f"📈 *𝐏𝐄𝐑𝐅𝐎𝐑𝐌𝐀𝐍𝐂𝐄*\n\n• Successes: `{ts}`\n• Failures: `{tf}`\n• Rate: `{pct:.1f}%`",
                reply_markup=back_button("menu_botsettings"), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_targets":
            kb = [
                [InlineKeyboardButton("🎯 𝗦𝗘𝗧 𝗧𝗔𝗥𝗚𝗘𝗧", callback_data="tg_set")],
                [InlineKeyboardButton("🗑️ 𝗗𝗘𝗟𝗘𝗧𝗘 𝗧𝗔𝗥𝗚𝗘𝗧", callback_data="tg_del")],
                [InlineKeyboardButton("📋 𝗟𝗜𝗦𝗧 𝗧𝗔𝗥𝗚𝗘𝗧𝗦", callback_data="tg_list")],
                [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
            ]
            await safe_edit(q,
                "🎯 *𝐓𝐀𝐑𝐆𝐄𝐓𝐒*\n\nSet target users with labels (t1, t2...)\nUse as `.luffync1 t1`.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data == "tg_set":
            await safe_edit(q, "🎯 Reply to a user with `.settarget <label>`.",
                reply_markup=back_button("menu_targets")); return
        if data == "tg_del":
            await safe_edit(q, "🗑️ Reply to a user with `.deltarget`.",
                reply_markup=back_button("menu_targets")); return
        if data == "tg_list":
            txt = "❌ No targets." if not TARGETS else "📋 *𝐓𝐀𝐑𝐆𝐄𝐓𝐒*\n\n" + "\n".join(f"• `{lbl}` → `{uid}`" for uid, lbl in TARGETS.items())
            await safe_edit(q, txt, reply_markup=back_button("menu_targets"), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_pfp":
            kb = [
                [InlineKeyboardButton(".pfplock", callback_data="pfplock")],
                [InlineKeyboardButton(".pfploop", callback_data="pfploop")],
                [InlineKeyboardButton(".savepfp", callback_data="savepfp")],
                [InlineKeyboardButton(".allpfp", callback_data="allpfp")],
                [InlineKeyboardButton(".deletepfp", callback_data="deletepfp")],
                [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
            ]
            await safe_edit(q,
                "🖼️ *𝐏𝐅𝐏 𝐋𝐎𝐎𝐏*\n\n"
                "• `.pfplock` — stop\n• `.pfploop` — turbo loop\n"
                "• `.savepfp` — save image\n• `.allpfp` — set once\n• `.deletepfp` — clear",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data == "pfplock":
            cid = q.message.chat.id
            PFP_LOOP_STATE[cid] = False; save_pfp()
            n = _cancel_named(cid, "pfploop")
            await ans(f"🔒 Locked ({n} tasks).", True); return
        if data == "pfploop":
            cid = q.message.chat.id
            if not PFP_IMAGES.get(cid): await ans("❌ No pfps. Use .savepfp.", True); return
            PFP_LOOP_STATE[cid] = True; save_pfp()
            interval = get_interval(cid, "pfp")
            stop_ref = {"stop": False}
            _cancel_named(cid, "pfploop")
            tasks = [asyncio.create_task(_per_bot_pfp_worker(b, cid, PFP_IMAGES[cid], stop_ref, interval))
                     for b in all_bots()]
            for t in tasks: _track(cid, "pfploop", t)
            await ans(f"⚡ Loop started (interval {interval}s).", True); return
        if data == "savepfp":
            await safe_edit(q, "📸 Reply to a *photo* with `.savepfp`.",
                reply_markup=back_button("menu_pfp"), parse_mode=ParseMode.MARKDOWN); return
        if data == "allpfp":
            cid = q.message.chat.id
            if not PFP_IMAGES.get(cid): await ans("❌ No pfps.", True); return
            img = PFP_IMAGES[cid][0]
            coros = [safe_call(b["bot"].set_chat_photo, cid, photo=img, bot_id=b["id"], timeout=2.0)
                     for b in all_bots()]
            await asyncio.gather(*coros, return_exceptions=True)
            await ans("✅ Done.", True); return
        if data == "deletepfp":
            cid = q.message.chat.id
            PFP_IMAGES[cid] = []; PFP_LOOP_STATE[cid] = False; save_pfp()
            await ans("🗑️ Deleted.", True); return
        if data == "menu_fun":
            kb = [
                [InlineKeyboardButton(".play", callback_data="cmd_play"),
                 InlineKeyboardButton(".ai", callback_data="cmd_ai")],
                [InlineKeyboardButton(".cat", callback_data="cmd_cat"),
                 InlineKeyboardButton(".dog", callback_data="cmd_dog")],
                [InlineKeyboardButton(".dice", callback_data="cmd_dice"),
                 InlineKeyboardButton(".quotes", callback_data="cmd_quotes")],
                [InlineKeyboardButton(".jokes", callback_data="cmd_jokes"),
                 InlineKeyboardButton(".find", callback_data="cmd_find")],
                [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
            ]
            await safe_edit(q,
                "🎮 *𝐅𝐔𝐍 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\n"
                "• `.play <song>` — play music\n• `.ai <prompt>` — generate image\n"
                "• `.cat` — random cat\n• `.dog` — random dog\n• `.dice` — roll dice\n"
                "• `.quotes` — quote\n• `.jokes` — joke\n• `.find <music>` — find",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data == "cmd_cat":
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get("https://api.thecatapi.com/v1/images/search") as r:
                        url = (await r.json())[0]["url"]
                await context.bot.send_photo(q.message.chat.id, url); await ans("🐱")
            except Exception as e: await ans(f"❌ {e}", True)
            return
        if data == "cmd_dog":
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get("https://dog.ceo/api/breeds/image/random") as r:
                        url = (await r.json())["message"]
                await context.bot.send_photo(q.message.chat.id, url); await ans("🐶")
            except Exception as e: await ans(f"❌ {e}", True)
            return
        if data == "cmd_dice":
            try: await context.bot.send_dice(chat_id=q.message.chat.id, emoji="🎲"); await ans("🎲")
            except Exception as e: await ans(f"❌ {e}", True)
            return
        if data == "cmd_quotes":
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get("https://zenquotes.io/api/random") as r:
                        qq = (await r.json())[0]
                await context.bot.send_message(q.message.chat.id, f"💭 \"{qq['q']}\"\n\n— *{qq['a']}*", parse_mode=ParseMode.MARKDOWN)
                await ans("💭")
            except Exception as e: await ans(f"❌ {e}", True)
            return
        if data == "cmd_jokes":
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get("https://official-joke-api.appspot.com/random_joke") as r:
                        d = await r.json()
                await context.bot.send_message(q.message.chat.id, f"😂 {d['setup']}\n\n{d['punchline']}")
                await ans("😂")
            except Exception as e: await ans(f"❌ {e}", True)
            return
        if data in ("cmd_play", "cmd_ai", "cmd_find"):
            cm = {"cmd_play": ".play <song>", "cmd_ai": ".ai <prompt>", "cmd_find": ".find <music>"}
            await safe_edit(q, f"🎮 *{cm[data]}*\n\nType `{cm[data]}` in chat.",
                reply_markup=back_button("menu_fun"), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_group":
            kb = [
                [InlineKeyboardButton(".lock", callback_data="gc_lock"),
                 InlineKeyboardButton(".unlock", callback_data="gc_unlock")],
                [InlineKeyboardButton(".promote", callback_data="gc_promote"),
                 InlineKeyboardButton(".demote", callback_data="gc_demote")],
                [InlineKeyboardButton(".admin", callback_data="gc_admin"),
                 InlineKeyboardButton(".mute", callback_data="gc_mute")],
                [InlineKeyboardButton(".unmute", callback_data="gc_unmute"),
                 InlineKeyboardButton(".kick", callback_data="gc_kick")],
                [InlineKeyboardButton(".ban", callback_data="gc_ban"),
                 InlineKeyboardButton(".unban", callback_data="gc_unban")],
                [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
            ]
            await safe_edit(q, "🛡️ *𝐆𝐑𝐎𝐔𝐏 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒*\n\nAll commands work 100%.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data == "gc_lock":
            chat = q.message.chat
            if chat.type not in ("group", "supergroup"): await ans("❌ Use in group.", True); return
            perms = ChatPermissions(can_send_messages=False)
            n = 0
            for b in all_bots():
                try: await b["bot"].set_chat_permissions(chat.id, perms); n += 1
                except: pass
            await ans(f"🔒 Locked ({n} bots).", True); return
        if data == "gc_unlock":
            chat = q.message.chat
            if chat.type not in ("group", "supergroup"): await ans("❌ Use in group.", True); return
            perms = ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                                    can_send_polls=True, can_send_other_messages=True,
                                    can_add_web_page_previews=True, can_change_info=True,
                                    can_invite_users=True, can_pin_messages=True)
            n = 0
            for b in all_bots():
                try: await b["bot"].set_chat_permissions(chat.id, perms); n += 1
                except: pass
            await ans(f"🔓 Unlocked ({n} bots).", True); return
        if data == "gc_admin":
            chat = q.message.chat
            if chat.type not in ("group", "supergroup"): await ans("❌ Use in group.", True); return
            n = 0
            for b in all_bots():
                try:
                    await b["bot"].promote_chat_member(chat.id, b["id"],
                        can_change_info=True, can_delete_messages=True, can_invite_users=True,
                        can_restrict_members=True, can_pin_messages=True, can_promote_members=True,
                        can_manage_video_chats=True, can_manage_chat=True); n += 1
                except: pass
            await ans(f"👑 Promoted {n}/{len(all_bots())} bots.", True); return
        if data in ("gc_promote", "gc_demote", "gc_mute", "gc_unmute", "gc_kick", "gc_ban", "gc_unban"):
            mp = {"gc_promote": ".promote", "gc_demote": ".demote", "gc_mute": ".mute",
                  "gc_unmute": ".unmute", "gc_kick": ".kick", "gc_ban": ".ban", "gc_unban": ".unban"}
            cmd = mp[data]
            await safe_edit(q, f"🛡️ *{cmd}*\n\nReply to a user with `{cmd}`.",
                reply_markup=back_button("menu_group"), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_stop":
            await safe_edit(q,
                "🛑 *𝐒𝐓𝐎𝐏 𝐓𝐀𝐒𝐊*\n\n• `.s <command_name>` — stop specific task\n• `.sall` — stop ALL tasks instantly ⚡",
                reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_speed":
            cur = CHAT_INTERVALS.get(q.message.chat.id, {})
            lines = ["⚡ *𝐒𝐏𝐄𝐄𝐃 𝐂𝐎𝐍𝐓𝐑𝐎𝐋*", ""]
            for k, v in DEFAULT_INTERVALS.items():
                lines.append(f"• `{k}` = {cur.get(k, v)}s")
            lines.append("\n`.speed <cat> <seconds>` — e.g. `.speed all 0.01`")
            await safe_edit(q, "\n".join(lines),
                reply_markup=back_button("menu_main"), parse_mode=ParseMode.MARKDOWN); return
        if data == "menu_edits":
            kb = [
                [InlineKeyboardButton("🖼️ 𝐄𝐃𝐈𝐓 𝐒𝐓𝐀𝐑𝐓 𝐌𝐄𝐍𝐔 𝐌𝐄𝐃𝐈𝐀", callback_data="ed_startmedia")],
                [InlineKeyboardButton("📝 𝐄𝐃𝐈𝐓 𝐒𝐓𝐀𝐑𝐓 𝐓𝐄𝐗𝐓", callback_data="ed_starttext")],
                [InlineKeyboardButton("🔄 𝐑𝐄𝐒𝐄𝐓 𝐓𝐎 𝐃𝐄𝐅𝐀𝐔𝐋𝐓", callback_data="ed_resetstart")],
                [InlineKeyboardButton("🎬 𝐄𝐃𝐈𝐓 𝐆𝐀𝐌𝐄 𝐎𝐕𝐄𝐑 𝐌𝐄𝐃𝐈𝐀", callback_data="ed_gomedia")],
                [InlineKeyboardButton("➕ 𝐀𝐃𝐃 𝐒𝐔𝐃𝐎", callback_data="ed_addsudo")],
                [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
            ]
            await safe_edit(q, "✏️ *𝐄𝐃𝐈𝐓𝐒*\n\nConfigure start text, media, sudo.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN); return
        if data == "ed_startmedia":
            await safe_edit(q, "🖼️ Send a photo/video with caption `.setstartmedia`.",
                reply_markup=back_button("menu_edits")); return
        if data == "ed_starttext":
            cur = CFG["start_text"][:200] + ("..." if len(CFG["start_text"]) > 200 else "")
            await safe_edit(q,
                f"📝 *CURRENT START TEXT:*\n\n{cur}\n\n"
                f"Use `.setstarttext <new text>` to update.",
                reply_markup=back_button("menu_edits"), parse_mode=ParseMode.MARKDOWN); return
        if data == "ed_resetstart":
            CFG["start_text"] = DEFAULT_MENU_HEADER
            CFG["start_media_type"] = None
            CFG["start_media_file_id"] = None
            save_config()
            await ans("✅ Reset to default branding.", True); return
        if data == "ed_gomedia":
            await safe_edit(q, "🎬 Send a photo/video with caption `.setgomedia`.",
                reply_markup=back_button("menu_edits")); return
        if data == "ed_addsudo":
            await safe_edit(q, "➕ Reply to a user with `.ok`.",
                reply_markup=back_button("menu_edits")); return
        if data.startswith("cmd_luffync_"):
            n = data.rsplit("_", 1)[1]
            await safe_edit(q, f"🇱 🇺 🇫 🇫 🇾  ɴᴄ {n}\n\nUsage: `.luffync{n} <text>`",
                reply_markup=back_button("menu_luffy")); return
        if data.startswith("cmd_vegetanc_"):
            n = data.rsplit("_", 1)[1]
            await safe_edit(q, f"🇻 🇪 🇬 🇪 🇹 🇦  ɴᴄ {n}\n\nUsage: `.vegetanc{n} <text>`",
                reply_markup=back_button("menu_vegeta")); return
        if data.startswith("cmd_spam_"):
            n = data.rsplit("_", 1)[1]
            await safe_edit(q, f"💥 𝐒𝐏𝐀𝐌 {n}\n\nUsage: `.spam{n} <text>`",
                reply_markup=back_button("menu_spam")); return
        await ans("⚠️ Unknown action", True)
    except Exception as e:
        log.exception(f"callback_router crashed: {e}")
        try: await q.answer("❌ Error occurred", show_alert=True)
        except Exception: pass
        answered["v"] = True
    finally:
        if not answered["v"]:
            try: await q.answer()
            except Exception: pass

# ═══════════════════════════════════════════════════════════════════════
#   HANDLER REGISTRATION
# ═══════════════════════════════════════════════════════════════════════

def register_master_handlers(app: Application):
    D = DotCommandHandler
    app.add_handler(D("start", start_cmd))
    app.add_handler(D("menu", start_cmd))
    app.add_handler(D("add", add_bot_cmd))
    app.add_handler(D("delbot", del_bot_cmd))
    app.add_handler(D("ok", add_sudo_cmd))
    app.add_handler(D("delok", del_sudo_cmd))
    app.add_handler(D("sudo", list_sudo_cmd))
    app.add_handler(D("setstarttext", setstarttext_cmd))
    app.add_handler(D("resetstart", resetstart_cmd))
    app.add_handler(D("setstartmedia", setstartmedia_cmd))
    app.add_handler(D("setgomedia", setgomedia_cmd))
    app.add_handler(D("dfn", gameover_cmd))
    app.add_handler(D("settarget", set_target_cmd))
    app.add_handler(D("deltarget", del_target_cmd))
    app.add_handler(D("s", stop_task_cmd))
    app.add_handler(D("sall", stop_all_cmd))
    app.add_handler(D("speed", speed_cmd))
    app.add_handler(CallbackQueryHandler(callback_router))

def register_child_handlers(app: Application):
    D = DotCommandHandler
    for i in range(1, 11):
        app.add_handler(D(f"luffync{i}", luffy_nc_cmd))
        app.add_handler(D(f"vegetanc{i}", vegeta_nc_cmd))
    for i in range(1, 6):
        app.add_handler(D(f"spam{i}", spam_cmd))
    for c, h in [("rr", rr_cmd), ("chud", chud_cmd), ("heartrr", heartrr_cmd),
                 ("flagrr", flagrr_cmd), ("pille", pille_cmd), ("slide", slide_cmd)]:
        app.add_handler(D(c, h))
    for c, h in [("lock", lock_cmd), ("unlock", unlock_cmd), ("promote", promote_cmd),
                 ("demote", demote_cmd), ("admin", admin_cmd), ("mute", mute_cmd),
                 ("unmute", unmute_cmd), ("kick", kick_cmd), ("ban", ban_cmd), ("unban", unban_cmd)]:
        app.add_handler(D(c, h))
    for c, h in [("cat", cat_cmd), ("dog", dog_cmd), ("dice", dice_cmd),
                 ("quotes", quotes_cmd), ("jokes", jokes_cmd),
                 ("ai", ai_cmd), ("find", find_cmd), ("play", play_cmd)]:
        app.add_handler(D(c, h))
    for c, h in [("savepfp", savepfp_cmd), ("allpfp", allpfp_cmd),
                 ("pfplock", pfplock_cmd), ("pfploop", pfploop_cmd),
                 ("deletepfp", deletepfp_cmd)]:
        app.add_handler(D(c, h))
    app.add_handler(D("s", stop_task_cmd))
    app.add_handler(D("sall", stop_all_cmd))
    app.add_handler(D("speed", speed_cmd))
    app.add_handler(D("settarget", set_target_cmd))
    app.add_handler(D("deltarget", del_target_cmd))
    app.add_handler(D("dfn", gameover_cmd))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & GROUP_FILTER,
        slide_message_handler), group=99)

# ═══════════════════════════════════════════════════════════════════════
#   MAIN — with post_init manual call fix
# ═══════════════════════════════════════════════════════════════════════

async def _post_init_master(app: Application):
    try:
        me = await app.bot.get_me()
        log.info(f"✅ Master @{me.username} online")
    except Exception as e:
        log.error(f"Master bot error: {e}")

async def main_async():
    master = ApplicationBuilder().token(BOT_TOKEN).post_init(_post_init_master).build()
    register_master_handlers(master)

    await master.initialize()
    # ⚠️ FIX: manually call post_init since we're not using run_polling()
    if master.post_init:
        try:
            await master.post_init(master)
        except Exception as e:
            log.error(f"post_init error: {e}")

    await master.start()
    await master.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    log.info("🚀 LUFFY CREW v5.4 FINAL starting...")

    log.info("📥 Loading child bots from disk...")
    await CHILD_MGR.start_all_from_disk()
    log.info(f"📊 Child bots active: {len(all_bots())} | Sudo: {len(SUDO_USERS)} | Owner: {OWNER_ID}")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        log.info("🛑 Shutting down...")
        await CHILD_MGR.stop_all()
        try: await master.updater.stop()
        except: pass
        try: await master.stop()
        except: pass
        try: await master.shutdown()
        except: pass

def main():
    if BOT_TOKEN == "YOUR_MAIN_BOT_TOKEN_HERE" or not OWNER_ID:
        print("⚠️ Set BOT_TOKEN and OWNER_ID env vars.")
        sys.exit(1)
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        log.info("Interrupted.")

if __name__ == "__main__":
    main()