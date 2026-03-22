"""
Admin Commands Module
Handles all admin functionalities
"""

import os
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo
from pyrogram.enums import ParseMode
from datetime import datetime

import sys
sys.path.append('..')
from utils.database import db

# Admin user ID
ADMIN_ID = 8453431521

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == ADMIN_ID

def get_banned_video():
    """Get random video from Banned folder"""
    banned_folder = "Banned"
    if os.path.exists(banned_folder):
        videos = [f for f in os.listdir(banned_folder) if f.endswith('.mp4')]
        if videos:
            return os.path.join(banned_folder, random.choice(videos))
    return None

def get_maintenance_video():
    """Get random video from Maintenance folder"""
    maintenance_folder = "Maintenance"
    if os.path.exists(maintenance_folder):
        videos = [f for f in os.listdir(maintenance_folder) if f.endswith('.mp4')]
        if videos:
            return os.path.join(maintenance_folder, random.choice(videos))
    return None

def setup_admin_commands(app: Client):
    """Setup all admin commands"""
    
    @app.on_message(filters.command(["broadcast"], prefixes=[".", "/", "!", "$"]) & filters.user(ADMIN_ID))
    async def broadcast_command(client, message):
        """Broadcast message to all users"""
        if not message.reply_to_message:
            await message.reply_text("❌ Reply to a message to broadcast it")
            return
        
        users = db.get_all_users()
        total = len(users)
        success = 0
        failed = 0
        
        progress_msg = await message.reply_text(f"📡 Broadcasting to {total} users...")
        
        for user in users:
            try:
                user_id = user["user_id"]
                
                # Forward the message
                if message.reply_to_message.text:
                    await client.send_message(user_id, message.reply_to_message.text)
                elif message.reply_to_message.photo:
                    await client.send_photo(user_id, message.reply_to_message.photo.file_id, 
                                          caption=message.reply_to_message.caption)
                elif message.reply_to_message.video:
                    await client.send_video(user_id, message.reply_to_message.video.file_id,
                                          caption=message.reply_to_message.caption)
                elif message.reply_to_message.audio:
                    await client.send_audio(user_id, message.reply_to_message.audio.file_id,
                                          caption=message.reply_to_message.caption)
                elif message.reply_to_message.document:
                    await client.send_document(user_id, message.reply_to_message.document.file_id,
                                             caption=message.reply_to_message.caption)
                
                success += 1
            except Exception as e:
                failed += 1
                print(f"Failed to send to {user_id}: {e}")
        
        await progress_msg.edit_text(
            f"✅ Broadcast Complete!\n\n"
            f"Total Users: {total}\n"
            f"Success: {success}\n"
            f"Failed: {failed}"
        )
    
    @app.on_message(filters.command(["maintenance", "maint"], prefixes=[".", "/", "!", "$"]) & filters.user(ADMIN_ID))
    async def maintenance_command(client, message):
        """Toggle maintenance mode"""
        current_status = db.is_maintenance()
        new_status = not current_status
        db.set_maintenance(new_status)
        
        status_text = "ON ✅" if new_status else "OFF ❌"
        await message.reply_text(f"🔧 Maintenance Mode: {status_text}")
    
    @app.on_message(filters.command(["ftm"], prefixes=[".", "/", "!", "$"]) & filters.user(ADMIN_ID))
    async def forward_to_me_command(client, message):
        """Toggle forward to admin mode"""
        current_status = db.is_forward_to_admin()
        new_status = not current_status
        db.set_forward_to_admin(new_status)
        
        status_text = "ON ✅" if new_status else "OFF ❌"
        await message.reply_text(f"📨 Forward to Admin: {status_text}")
    
    @app.on_message(filters.command(["stats"], prefixes=[".", "/", "!", "$"]) & filters.user(ADMIN_ID))
    async def stats_command(client, message):
        """Show bot statistics"""
        stats = db.get_stats()
        users = db.get_all_users()
        
        premium_count = sum(1 for u in users if db.is_premium(u["user_id"]))
        banned_count = sum(1 for u in users if u.get("is_banned", False))
        
        gateway_stats = "\n".join([f"  {gateway}: {count}" for gateway, count in stats["checks_by_gateway"].items()])
        
        stats_text = f"""📊 <b>Bot Statistics</b>

👥 Total Users: {stats['total_users']}
💎 Premium Users: {premium_count}
🚫 Banned Users: {banned_count}

📈 Total Checks: {stats['total_checks']}

<b>Checks by Gateway:</b>
{gateway_stats if gateway_stats else '  None yet'}

🔧 Maintenance: {'ON' if db.is_maintenance() else 'OFF'}
📨 Forward to Admin: {'ON' if db.is_forward_to_admin() else 'OFF'}
"""
        
        await message.reply_text(stats_text, parse_mode=ParseMode.HTML)
    
    @app.on_message(filters.command(["ban"], prefixes=[".", "/", "!", "$"]) & filters.user(ADMIN_ID))
    async def ban_command(client, message):
        """Ban a user"""
        # Get user ID from reply or command argument
        target_user_id = None
        target_username = None
        
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username
        elif len(message.command) > 1:
            try:
                target_user_id = int(message.command[1])
            except:
                await message.reply_text("❌ Invalid user ID")
                return
        else:
            await message.reply_text("❌ Reply to a user or provide user ID")
            return
        
        if db.ban_user(target_user_id):
            await message.reply_text(f"✅ User {target_user_id} banned")
        else:
            await message.reply_text("❌ Failed to ban user")
    
    @app.on_message(filters.command(["unban"], prefixes=[".", "/", "!", "$"]) & filters.user(ADMIN_ID))
    async def unban_command(client, message):
        """Unban a user"""
        target_user_id = None
        
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        elif len(message.command) > 1:
            try:
                target_user_id = int(message.command[1])
            except:
                await message.reply_text("❌ Invalid user ID")
                return
        else:
            await message.reply_text("❌ Reply to a user or provide user ID")
            return
        
        if db.unban_user(target_user_id):
            await message.reply_text(f"✅ User {target_user_id} unbanned")
        else:
            await message.reply_text("❌ Failed to unban user")
    
    @app.on_message(filters.command(["addp"], prefixes=[".", "/", "!", "$"]) & filters.user(ADMIN_ID))
    async def add_premium_command(client, message):
        """Add premium to a user"""
        # Parse command: /addp duration [user_id]
        # Or reply to message: /addp duration
        
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username
            
            if len(message.command) < 2:
                await message.reply_text("❌ Usage: /addp duration (e.g., /addp 30d)")
                return
            
            duration = message.command[1]
        elif len(message.command) >= 3:
            duration = message.command[1]
            try:
                target_user_id = int(message.command[2])
            except:
                # Maybe it's a username
                await message.reply_text("❌ Invalid user ID")
                return
            
            user = db.get_user(target_user_id)
            target_username = user.get("username") if user else None
        else:
            await message.reply_text("❌ Usage: /addp duration user_id OR reply to user with /addp duration")
            return
        
        success, result = db.add_premium(target_user_id, duration)
        
        if success:
            expiry_date = result.strftime("%d %b %Y")
            
            # Send receipt to user
            receipt = f"""<b>Premium Subscription Confirmed ✅️</b>
━━━━━━━━━━━━━━━━━━
👤 @{target_username or 'user'}
⏳ {duration.upper()} Access
📅 Until: {expiry_date}
🆔 Ref: TXN-{datetime.now().year}-{target_user_id % 1000}

━━━━━━━━━━━━━━━━━━"""
            
            try:
                await client.send_message(target_user_id, receipt, parse_mode=ParseMode.HTML)
                await message.reply_text(f"✅ Premium added to user {target_user_id}\nReceipt sent to user")
            except:
                await message.reply_text(f"✅ Premium added but failed to send receipt to user")
        else:
            await message.reply_text(f"❌ Failed: {result}")
    
    @app.on_message(filters.command(["gate"], prefixes=[".", "/", "!", "$"]) & filters.user(ADMIN_ID))
    async def gate_command(client, message):
        """Lock/unlock a gateway"""
        # Usage: /gate ad off  OR  /gate ad on
        
        if len(message.command) < 3:
            await message.reply_text("❌ Usage: /gate <gateway> <on/off>")
            return
        
        gateway = message.command[1].lower()
        action = message.command[2].lower()
        
        if action == "off":
            db.lock_gateway(gateway)
            await message.reply_text(f"🔒 Gateway '{gateway}' locked")
        elif action == "on":
            db.unlock_gateway(gateway)
            await message.reply_text(f"🔓 Gateway '{gateway}' unlocked")
        else:
            await message.reply_text("❌ Action must be 'on' or 'off'")
    
    @app.on_message(filters.command(["premium_gate", "pgate"], prefixes=[".", "/", "!", "$"]) & filters.user(ADMIN_ID))
    async def premium_gate_command(client, message):
        """Make gateway premium-only"""
        # Usage: /premium_gate ad on  OR  /premium_gate ad off
        
        if len(message.command) < 3:
            await message.reply_text("❌ Usage: /premium_gate <gateway> <on/off>")
            return
        
        gateway = message.command[1].lower()
        action = message.command[2].lower()
        
        if action == "on":
            db.add_premium_gateway(gateway)
            await message.reply_text(f"💎 Gateway '{gateway}' is now premium-only")
        elif action == "off":
            db.remove_premium_gateway(gateway)
            await message.reply_text(f"🆓 Gateway '{gateway}' is now free")
        else:
            await message.reply_text("❌ Action must be 'on' or 'off'")
    
    print("✅ Admin commands registered")

# Middleware functions to check before processing commands

async def check_banned(client, message):
    """Check if user is banned"""
    user_id = message.from_user.id
    
    if db.is_banned(user_id):
        video = get_banned_video()
        caption = f"<b>User.status = '<a href='tg://user?id={user_id}'>BANNED</a>'</b>"
        
        if video and os.path.exists(video):
            await message.reply_video(video, caption=caption, parse_mode=ParseMode.HTML)
        else:
            await message.reply_text(caption, parse_mode=ParseMode.HTML)
        
        return True
    return False

async def check_maintenance(client, message):
    """Check if bot is in maintenance"""
    user_id = message.from_user.id
    
    # Admin bypasses maintenance
    if is_admin(user_id):
        return False
    
    if db.is_maintenance():
        video = get_maintenance_video()
        caption = f"<b>Can't you see ?</b> ⇾ <a href='https://t.me/themigel'>㊕</a> <b>Maintainance</b> <a href='https://t.me/themigel'>㊕</a>"
        
        if video and os.path.exists(video):
            await message.reply_video(video, caption=caption, parse_mode=ParseMode.HTML)
        else:
            await message.reply_text(caption, parse_mode=ParseMode.HTML)
        
        return True
    return False

async def check_gateway_access(user_id, gateway):
    """Check if user can access gateway"""
    # Check if gateway is locked
    if db.is_gateway_locked(gateway):
        return False, "locked"
    
    # Check if gateway requires premium
    if db.is_gateway_premium(gateway):
        if not db.is_premium(user_id):
            return False, "premium"
    
    return True, None

async def forward_to_admin_if_enabled(client, message, gateway):
    """Forward message to admin if enabled"""
    if db.is_forward_to_admin():
        try:
            await message.forward(ADMIN_ID)
        except:
            pass
