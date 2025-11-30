# Don't Remove Credit Tg - https://t.me/roxybasicneedbot1
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@roxybasicneedbot
# Ask Doubt on telegram https://t.me/roxybasicneedbot1

import os
import re
import sys
import json
import time
import asyncio
import requests
import subprocess
import concurrent.futures

import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN, FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL_LINK, ADMINS, OWNER_ID
from aiohttp import ClientSession
from pyromod import listen
from subprocess import getstatusoutput

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserNotParticipant, ChatAdminRequired
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ParseMode, ChatMemberStatus

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN)

WELCOME_IMAGE_PATH = "welcome.jpg"

# ============================================================
# FAST M3U8 DOWNLOADER (32-thread parallel accelerator)
# ============================================================
async def fast_m3u8_download(url, output_name):
    print("⚡ Fast M3U8 Downloader Enabled...")

    try:
        playlist_text = requests.get(url).text
        base = url.rsplit("/", 1)[0]

        segments = [
            f"{base}/{line.strip()}"
            for line in playlist_text.splitlines()
            if line.endswith(".ts")
        ]

        os.makedirs("ts_temp", exist_ok=True)

        # download each .ts chunk
        def fetch(seg_url):
            name = seg_url.split("/")[-1]
            data = requests.get(seg_url).content
            with open(f"ts_temp/{name}", "wb") as f:
                f.write(data)
            return name

        # parallel download with 32 threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
            list(ex.map(fetch, segments))

        # merge segments
        with open(output_name, "wb") as v:
            for seg in segments:
                name = seg.split("/")[-1]
                with open(f"ts_temp/{name}", "rb") as f:
                    v.write(f.read())

        return output_name

    except Exception as e:
        print("M3U8 ERROR:", e)
        return None
        
# ============================================================
# FORCE SUBSCRIBE CHECK
# ============================================================

async def is_subscribed(bot, user_id):
    if not FORCE_SUB_CHANNEL:
        return True

    try:
        member = await bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        return member.status in [
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        ]
    except UserNotParticipant:
        return False
    except Exception:
        return False


def force_subscribe(func):
    async def wrapper(bot, message):
        if FORCE_SUB_CHANNEL:
            subscribed = await is_subscribed(bot, message.from_user.id)
            if not subscribed:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔔 Join Channel", url=FORCE_SUB_CHANNEL_LINK)],
                    [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_sub")]
                ])
                await message.reply_text(
                    "<b>🔒 Access Denied!</b>\n"
                    "You must join our channel to use this bot.",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                return

        await func(bot, message)

    return wrapper


# ============================================================
# URL PARSING HELPERS
# ============================================================

def is_valid_url(url):
    pattern = re.compile(
        r'^https?://'
    )
    return bool(pattern.match(url))


def extract_url_from_line(line):
    line = line.strip()
    if not line:
        return None, None

    match = re.search(r'https?://[^\s]+', line)
    if match:
        url = match.group()
        title = line.replace(url, '').strip()
        if not title:
            title = f"File_{hash(url) % 1000}"
        return title, url

    return None, None


# ============================================================
# START COMMAND
# ============================================================

@bot.on_message(filters.command(["start"]))
@force_subscribe
async def start(bot: Client, m: Message):

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Upload Files", callback_data="upload_files")],
        [
            InlineKeyboardButton("🔔 Channel", url="https://t.me/roxybasicneedbot1"),
            InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/roxycontactbot")
        ]
    ])

    welcome_text = (
        f"<b>👋 Hello {m.from_user.mention}!</b>\n\n"
        "<blockquote>"
        "📁 I am a bot for downloading files from your <b>.TXT</b> file "
        "and uploading them to Telegram.\n\n"
        "🚀 To get started, send /upload command."
        "</blockquote>"
    )

    if os.path.exists(WELCOME_IMAGE_PATH):
        await m.reply_photo(
            photo=WELCOME_IMAGE_PATH,
            caption=welcome_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await m.reply_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )


# ============================================================
# CALLBACK HANDLER
# ============================================================

@bot.on_callback_query()
async def callback_handler(bot: Client, query: CallbackQuery):
    data = query.data

    if data == "refresh_sub":
        subscribed = await is_subscribed(bot, query.from_user.id)
        if subscribed:
            await query.message.delete()
            await bot.send_message(query.from_user.id, "✅ Subscription Verified!\nSend /start to continue.")
        else:
            await query.answer("❌ You must join the channel first!", show_alert=True)

    elif data == "upload_files":
        await query.answer("Send /upload to start!", show_alert=True)
        
        # ============================================================
# STOP COMMAND
# ============================================================

@bot.on_message(filters.command("stop"))
async def restart_handler(_, m: Message):
    await m.reply_text("🛑 Stopped")
    os.execl(sys.executable, sys.executable, *sys.argv)


# ============================================================
# UPLOAD COMMAND
# ============================================================

@bot.on_message(filters.command(["upload"]))
@force_subscribe
async def upload(bot: Client, m: Message):

    editable = await m.reply_text("📤 Send your TXT file with links ⚡")

    input_file: Message = await bot.listen(m.chat.id)
    txt_path = await input_file.download()
    await input_file.delete(True)

    # Create folder per chat
    path = f"./downloads/{m.chat.id}"
    os.makedirs(path, exist_ok=True)

    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().split("\n")

        links = []
        for line in lines:
            title, url = extract_url_from_line(line)
            if title and url and is_valid_url(url):
                links.append([title, url])

        os.remove(txt_path)

        if not links:
            await editable.edit("❌ No valid links found in the file!")
            return

    except Exception as e:
        await editable.edit(f"❌ Error reading file: {e}")
        if os.path.exists(txt_path):
            os.remove(txt_path)
        return

    await editable.edit(f"📊 Total Links Found: {len(links)}\n\n📝 Send starting number (default: 1)")
    msg0 = await bot.listen(m.chat.id)
    raw_text = msg0.text
    await msg0.delete(True)

    await editable.edit("📝 Enter batch name:")
    msg1 = await bot.listen(m.chat.id)
    batch_name = msg1.text
    await msg1.delete(True)

    await editable.edit("🎬 Select video quality:\n144, 240, 360, 480, 720, 1080")
    msg2 = await bot.listen(m.chat.id)
    raw_quality = msg2.text
    await msg2.delete(True)

    quality_map = {
        "144": "256x144", "240": "426x240", "360": "640x360",
        "480": "854x480", "720": "1280x720", "1080": "1920x1080"
    }
    resolution = quality_map.get(raw_quality, "UN")

    await editable.edit("💬 Enter caption:")
    msg3 = await bot.listen(m.chat.id)
    extra_caption = msg3.text
    await msg3.delete(True)

    await editable.edit("🖼 Send thumbnail URL or 'no':")
    msg4 = await bot.listen(m.chat.id)
    thumb_input = msg4.text
    await msg4.delete(True)

    await editable.delete()

    # -----------------
    # Download thumbnail
    # -----------------
    thumb = "no"
    if thumb_input.startswith("http"):
        try:
            getstatusoutput(f"wget '{thumb_input}' -O thumb.jpg")
            if os.path.exists("thumb.jpg"):
                thumb = "thumb.jpg"
        except:
            thumb = "no"

    # -----------------
    # Starting number
    # -----------------
    try:
        count = max(1, int(raw_text)) if raw_text.isdigit() else 1
    except:
        count = 1

    successful_downloads = 0
    failed_downloads = 0

    # ============================================================
    # MAIN DOWNLOAD LOOP
    # ============================================================

    try:
        for i in range(count - 1, len(links)):
            title, url = links[i]

            safe_title = re.sub(r'[<>:"/\\\\|?*]', '', title)[:50]
            display_name = f"{str(count).zfill(3)}) {safe_title}"

            # captions
            cc_video = (
                f"**📹 Video  #{str(count).zfill(3)}**\n"
                f"**📁 Title:** {safe_title}\n"
                f"**📦 Batch:** {batch_name}\n"
                f"{extra_caption}"
            )

            cc_doc = (
                f"**📄 Document #{str(count).zfill(3)}**\n"
                f"**📁 Title:** {safe_title}\n"
                f"**📦 Batch:** {batch_name}\n"
                f"{extra_caption}"
            )

            prog = await m.reply_text(
                f"⬇️ **Downloading...**\n\n"
                f"📁 **Name:** `{safe_title}`\n"
                f"🔗 **URL:** `{url[:99]}...`\n"
                f"📊 **Progress:** {count}/{len(links)}"
            )
            try:
                # ============================================================
                # SPECIAL CASE: GOOGLE DRIVE FILES
                # ============================================================
                if "drive.google.com" in url:
                    fixed_url = url.replace("file/d/", "uc?export=download&id=")\
                                   .replace("/view?usp=sharing", "")
                    filename = await helper.download(fixed_url, display_name)

                    if filename and os.path.exists(filename):
                        await bot.send_document(
                            chat_id=m.chat.id, document=filename, caption=cc_doc
                        )
                        os.remove(filename)
                        successful_downloads += 1

                    await prog.delete()
                    count += 1
                    time.sleep(1)
                    continue

                # ============================================================
                # SPECIAL CASE: PDF DIRECT LINKS
                # ============================================================
                if url.endswith(".pdf"):
                    cmd = f'yt-dlp -o "{display_name}.pdf" "{url}"'
                    subprocess.run(cmd, shell=True)

                    expected_file = f"{display_name}.pdf"
                    if os.path.exists(expected_file):
                        await bot.send_document(
                            chat_id=m.chat.id, document=expected_file, caption=cc_doc
                        )
                        os.remove(expected_file)
                        successful_downloads += 1
                    else:
                        failed_downloads += 1
                        await prog.edit("❌ PDF Download Failed")

                    await prog.delete()
                    count += 1
                    time.sleep(1)
                    continue

                # ============================================================
                # *** M3U8 SUPER-FAST DOWNLOADER PATCH (NEW) ***
                # ============================================================
                if url.endswith(".m3u8"):
                    filename = await fast_m3u8_download(url, f"{display_name}.mp4")

                    if filename and os.path.exists(filename):
                        await helper.send_vid(
                            bot, m, cc_video, filename, thumb, display_name, prog
                        )
                        successful_downloads += 1
                    else:
                        failed_downloads += 1
                        await prog.edit("❌ M3U8 download failed")

                    await prog.delete()
                    count += 1
                    time.sleep(1)
                    continue
                # ============================================================

                # ============================================================
                # NORMAL VIDEO DOWNLOAD (YOUTUBE, DIRECT MP4, ETC.)
                # ============================================================
                
                if "youtu" in url:

                    raw_quality = "720"  # force exact 720p

                    ytf = (
                        f"bestvideo[height=720]+bestaudio/"
                        f"bestvideo[height=720]/"
                        f"best[height=720]"
                    )

                    cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{display_name}.%(ext)s"'

                else:
                    cmd = f'yt-dlp -f "best" "{url}" -o "{display_name}.%(ext)s"'


                subprocess.run(cmd, shell=True)

                # detect downloaded file
                possible_exts = [".mp4", ".mkv", ".avi", ".webm", ".mov"]
                final_file = None

                for ext in possible_exts:
                    test_file = f"{display_name}{ext}"
                    if os.path.exists(test_file):
                        final_file = test_file
                        break

                if final_file:
                    await helper.send_vid(
                        bot, m, cc_video, final_file, thumb, display_name, prog
                    )
                    successful_downloads += 1
                else:
                    failed_downloads += 1
                    await prog.edit(f"❌ Failed: {safe_title}")

                await prog.delete()
                count += 1
                time.sleep(1)

            except FloodWait as e:
                await m.reply_text(f"⚠️ Rate limited. Waiting {e.x} seconds…")
                time.sleep(e.x)
                continue

            except Exception as err:
                failed_downloads += 1
                await prog.edit(f"❌ Error: {str(err)[:150]}")
                await asyncio.sleep(2)
                continue

        # END FOR LOOP

    except Exception as fatal:
        await m.reply_text(f"❌ FATAL ERROR: {fatal}")

    # ============================================================
    # FINAL SUMMARY
    # ============================================================
    summary = (
        f"🎉 **Download Complete!**\n\n"
        f"✅ **Successful:** {successful_downloads}\n"
        f"❌ **Failed:** {failed_downloads}\n"
        f"📊 **Total:** {successful_downloads + failed_downloads}"
    )

    await m.reply_text(summary)


# ============================================================
# BOT START
# ============================================================
if __name__ == "__main__":
    bot.run()
            
