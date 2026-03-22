"""
User Tools Module
Contains /hit, /bin, /gbin commands
"""

import os
import csv
import random
import re
import pycountry
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# Admin ID
ADMIN_ID = 7673618351

# BIN data cache
bin_data_cache = {}
csv_file_path = "bins_all.csv"

def load_bin_data():
    """Load BIN data from CSV file"""
    global bin_data_cache
    if not os.path.exists(csv_file_path):
        print(f"Warning: {csv_file_path} not found. BIN lookup will not work.")
        return
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            # Skip header if present
            reader = csv.reader(file)
            for row in reader:
                if row and row[0].isdigit():  # Check if first column is a number (BIN)
                    bin_number = row[0]
                    bin_data_cache[bin_number] = {
                        'bin': row[0],
                        'country': row[1] if len(row) > 1 else 'N/A',
                        'flag': row[2] if len(row) > 2 else '',
                        'brand': row[3] if len(row) > 3 else 'N/A',
                        'type': row[4] if len(row) > 4 else 'N/A',
                        'level': row[5] if len(row) > 5 else 'N/A',
                        'bank_name': row[6] if len(row) > 6 else 'N/A'
                    }
        print(f"✅ Loaded {len(bin_data_cache)} BIN records")
    except Exception as e:
        print(f"Error loading BIN data: {e}")

def get_country_name(code):
    """Convert country code to full country name"""
    try:
        country = pycountry.countries.get(alpha_2=code)
        return country.name if country else code
    except:
        return code

def get_bin_info_from_csv(fbin):
    """Get BIN info from cached data"""
    # Try exact match first
    if fbin in bin_data_cache:
        return bin_data_cache[fbin]
    
    # Try shorter BIN (8 digits, then 6)
    for length in [8, 6]:
        if len(fbin) >= length:
            partial_bin = fbin[:length]
            if partial_bin in bin_data_cache:
                return bin_data_cache[partial_bin]
    
    return None

def extract_bin(message):
    """Extract BIN from command or replied message"""
    try:
        # Check if it's a command with argument
        if message.text and len(message.text.split()) >= 2:
            bin_match = re.search(r'\b(\d{6,})\b', message.text.split()[1])
            if bin_match:
                return bin_match.group(1)
        
        # Check if it's a reply to a message
        if message.reply_to_message:
            reply_text = message.reply_to_message.text or message.reply_to_message.caption
            if reply_text:
                bin_match = re.search(r'\b(\d{6,})\b', reply_text)
                if bin_match:
                    return bin_match.group(1)
        
        return None
    except:
        return None

def search_bins_in_csv(prefix):
    """Search for all bins starting with the given prefix"""
    matching_bins = []
    for bin_num, bin_info in bin_data_cache.items():
        if bin_num.startswith(prefix):
            matching_bins.append(bin_info)
    return matching_bins

def get_bins_for_page(matching_bins, page, bins_per_page=3):
    """Get bins for a specific page"""
    start_index = page * bins_per_page
    end_index = start_index + bins_per_page
    return matching_bins[start_index:end_index]

def create_gbin_keyboard(user_id, prefix, current_page, total_pages):
    """Create keyboard with navigation buttons for GBIN"""
    keyboard = []
    
    # Navigation buttons
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"gbin_prev_{user_id}_{prefix}_{current_page}"))
    
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"gbin_next_{user_id}_{prefix}_{current_page}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Exit button
    keyboard.append([InlineKeyboardButton("𝗘𝘅𝗶𝘁⚠️", callback_data=f"gbin_exit_{user_id}_{prefix}_{current_page}")])
    
    return InlineKeyboardMarkup(keyboard)

def get_hit_video():
    """Get random video from HIT folder"""
    hit_folder = "HIT"
    if os.path.exists(hit_folder):
        videos = [f for f in os.listdir(hit_folder) if f.endswith('.mp4')]
        if videos:
            return os.path.join(hit_folder, random.choice(videos))
    return None

def setup_user_tools(app: Client):
    """Setup all user tool commands"""
    
    # Load BIN data on startup
    load_bin_data()
    
    # /hit command
    @app.on_message(filters.command(["hit"], prefixes=[".", "/", "!", "$"]))
    async def hit_command(client, message):
        """Handle /hit command - photo submission"""
        user_id = message.from_user.id
        
        # Check if replying to a photo
        if not message.reply_to_message or not message.reply_to_message.photo:
            await message.reply_text(
                "❌ Reply to a photo with /hit to submit it for review",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Forward photo to admin
        try:
            await message.reply_to_message.forward(ADMIN_ID)
            
            # Send confirmation to user with video from HIT folder
            video = get_hit_video()
            caption = f"<b>UNDER REVIEW By <a href='https://t.me/amkush'>:)</a></b>"
            
            if video and os.path.exists(video):
                await message.reply_video(
                    video=video,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.reply_text(caption, parse_mode=ParseMode.HTML)
        
        except Exception as e:
            print(f"Error in hit command: {e}")
            await message.reply_text("❌ Error submitting photo", parse_mode=ParseMode.HTML)
    
    # /bin command
    @app.on_message(filters.command(["bin"], prefixes=[".", "/"]))
    async def bin_command(client, message):
        """Handle /bin command - BIN lookup"""
        user_id = message.from_user.id
        
        # Extract BIN from message
        bin_input = extract_bin(message)
        
        if not bin_input:
            # Invalid BIN format
            zero_symbol = f"<a href='tg://user?id={user_id}'>零</a>"
            north_symbol = f"<a href='tg://user?id={user_id}'>北</a>"
            jiu_symbol = f"<a href='tg://user?id={user_id}'>〆</a>"
            
            resp = f"""
〈{jiu_symbol}〉:(

〈{north_symbol}〉Invalid BIN! ⚠️

𝐌𝐞𝐬𝐬𝐚𝐠𝐞: 𝐍𝐨 𝐕𝐚𝐥𝐢𝐝 𝐁𝐈𝐍 𝐰𝐚𝐬 𝐟𝐨𝐮𝐧𝐝 𝐢𝐧 𝐲𝐨𝐮𝐫 𝐢𝐧𝐩𝐮𝐭.
"""
            await message.reply_text(resp, quote=True)
            return
        
        fbin = bin_input[:6]  # Take first 6 digits
        bin_info = get_bin_info_from_csv(fbin)
        
        if not bin_info:
            # BIN not found in database
            zero_symbol = f"<a href='tg://user?id={user_id}'>零</a>"
            north_symbol = f"<a href='tg://user?id={user_id}'>北</a>"
            jiu_symbol = f"<a href='tg://user?id={user_id}'>〆</a>"
            
            resp = f"""
〈{jiu_symbol}〉:(

〈{north_symbol}〉Invalid BIN! ⚠️

𝐌𝐞𝐬𝐬𝐚𝐠𝐞: 𝐍𝐨 𝐕𝐚𝐥𝐢𝐝 𝐁𝐈𝐍 𝐢𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧 𝐟𝐨𝐮𝐧𝐝 𝐢𝐧 𝐭𝐡𝐞 𝐝𝐚𝐭𝐚𝐛𝐚𝐬𝐞.
"""
            await message.reply_text(resp, quote=True)
            return
        
        # Format the response
        brand = bin_info.get("brand", "N/A").upper()
        card_type = bin_info.get("type", "N/A").upper()
        level = bin_info.get("level", "N/A").upper()
        bank = bin_info.get("bank_name", "N/A")
        country_code = bin_info.get("country", "N/A")
        flag = bin_info.get("flag", "")
        country_full_name = get_country_name(country_code).upper()
        
        # Create hyperlinked symbols
        zero_symbol = f"<a href='tg://user?id={user_id}'>零</a>"
        
        # Create user link
        user_link = f"<a href='tg://user?id={user_id}'>𝙈𝙞𝙜𝙚𝙡</a>"
        
        resp = f"""
〈{zero_symbol}〉𝘽𝙞𝙣 -» {fbin}
——————✵◦✵◦✵——————
〈{zero_symbol}〉𝙄𝙣𝙛𝙤 -» {brand} - {card_type} - {level}
〈{zero_symbol}〉𝘽𝙖𝙣𝙠 -» {bank}
〈{zero_symbol}〉𝘾𝙤𝙪𝙣𝙩𝙧𝙮 -» {country_full_name} {flag}
——————✵◦✵◦✵——————
〈{zero_symbol}〉𝘾𝙝𝙚𝙘𝙠𝙚𝙙 -» {user_link}
——————✵◦✵◦✵——————
"""
        
        # Create inline keyboard with Exit button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("𝗘𝘅𝗶𝘁⚠️", callback_data=f"exit_bin_{user_id}_{message.id}")]
        ])
        
        await message.reply_text(
            resp,
            quote=True,
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
    
    # /gbin command
    @app.on_message(filters.command(["gbin"], prefixes=[".", "/"]))
    async def gbin_command(client, message):
        """Handle /gbin command - BIN generator/search"""
        user_id = message.from_user.id
        
        # Extract prefix from message
        if not message.text or len(message.text.split()) < 2:
            # Invalid format
            jiu_symbol = f"<a href='tg://user?id={user_id}'>〆</a>"
            north_symbol = f"<a href='tg://user?id={user_id}'>北</a>"
            
            resp = f"""
〈{jiu_symbol}〉𝙎𝙮𝙨𝙩𝙚𝙢  

〈{north_symbol}〉 Invalid input ! ⚠
"""
            await message.reply_text(resp, quote=True)
            return
        
        prefix = message.text.split()[1].strip()
        
        # Validate prefix (should be numeric and between 1-6 digits)
        if not prefix.isdigit() or len(prefix) < 1 or len(prefix) > 6:
            jiu_symbol = f"<a href='tg://user?id={user_id}'>〆</a>"
            north_symbol = f"<a href='tg://user?id={user_id}'>北</a>"
            
            resp = f"""
〈{jiu_symbol}〉𝙎𝙮𝙨𝙩𝙚𝙢  

〈{north_symbol}〉 Invalid input ! ⚠
"""
            await message.reply_text(resp, quote=True)
            return
        
        # Search for matching bins
        matching_bins = search_bins_in_csv(prefix)
        
        if not matching_bins:
            jiu_symbol = f"<a href='tg://user?id={user_id}'>〆</a>"
            north_symbol = f"<a href='tg://user?id={user_id}'>北</a>"
            
            resp = f"""
〈{jiu_symbol}〉𝙎𝙮𝙨𝙩𝙚𝙢  

〈{north_symbol}〉 No BINs found starting with {prefix} ⚠
"""
            await message.reply_text(resp, quote=True)
            return
        
        # Get bins for first page
        bins_per_page = 3
        total_pages = (len(matching_bins) + bins_per_page - 1) // bins_per_page
        page_bins = get_bins_for_page(matching_bins, 0, bins_per_page)
        
        # Create hyperlinked symbols
        a_symbol = f"<a href='tg://user?id={user_id}'>ア</a>"
        ki_symbol = f"<a href='tg://user?id={user_id}'>キ</a>"
        ka_symbol = f"<a href='tg://user?id={user_id}'>カ</a>"
        shu_symbol = f"<a href='tg://user?id={user_id}'>朱</a>"
        zero_symbol = f"<a href='tg://user?id={user_id}'>零</a>"
        gen_symbol = f"<a href='tg://user?id={user_id}'>ᥫ᭡</a>"
        user_link = f"<a href='tg://user?id={user_id}'>ª𝗺𝗸𝘂𝘀𝗵</a>"
        
        # Build response with multiple bins
        resp = f"〈{a_symbol}〉𝙎𝙚𝙚𝙙 -» {prefix}xxx\n"
        resp += "- - - - - - - - - - - - - - - - - - - - -\n"
        
        for i, bin_info in enumerate(page_bins):
            brand = bin_info.get("brand", "N/A").upper()
            card_type = bin_info.get("type", "N/A").upper()
            level = bin_info.get("level", "N/A").upper()
            bank = bin_info.get("bank_name", "N/A")
            country_code = bin_info.get("country", "N/A")
            flag = bin_info.get("flag", "")
            country_full_name = get_country_name(country_code).upper()
            
            resp += f"〈{ki_symbol}〉𝘽𝙞𝙣 -» {bin_info['bin']}\n"
            resp += f"〈{ka_symbol}〉𝙄𝙣𝙛𝙤 -» {brand} - {card_type} - {level}\n"
            resp += f"〈{shu_symbol}〉𝘽𝙖𝙣𝙠 -» {bank}\n"
            resp += f"〈{zero_symbol}〉𝘾𝙤𝙪𝙣𝙩𝙧y -» {country_full_name} {flag}\n"
            
            if i < len(page_bins) - 1:
                resp += "- - - - - - - - - - - - - - - - - - - - -\n"
        
        resp += f"- - - - - - - - - - - - - - - - - - - - -\n"
        resp += f"〈{ki_symbol}〉𝙋𝙖𝙜𝙚 -» 1/{total_pages}\n"
        resp += f"- - - - - - - - - - - - - - - - - - - - -\n"
        resp += f"〈{gen_symbol}〉 𝙂𝙚𝙣 𝙗𝙮 -» {user_link}"
        
        # Create keyboard
        keyboard = create_gbin_keyboard(user_id, prefix, 0, total_pages)
        
        await message.reply_text(resp, quote=True, reply_markup=keyboard, disable_web_page_preview=True)
    
    # Callback handlers
    @app.on_callback_query(filters.regex(r"^exit_bin_"))
    async def handle_bin_exit_button(client, callback_query):
        """Handle BIN exit button"""
        try:
            data_parts = callback_query.data.split('_')
            original_user_id = int(data_parts[2])
            
            if callback_query.from_user.id == original_user_id:
                await callback_query.message.delete()
                await callback_query.answer()
            else:
                await callback_query.answer("⚠️ This is not your BIN check!", show_alert=True)
        except:
            await callback_query.answer()
    
    @app.on_callback_query(filters.regex(r"^gbin_"))
    async def handle_gbin_buttons(client, callback_query):
        """Handle GBIN navigation buttons"""
        try:
            data_parts = callback_query.data.split('_')
            action = data_parts[1]
            user_id = int(data_parts[2])
            search_prefix = data_parts[3]
            current_page = int(data_parts[4])
            
            # Check if the user clicking is the same as the original user
            if callback_query.from_user.id != user_id:
                await callback_query.answer("⚠️ This is not your search! Use /gbin to start your own search.", show_alert=True)
                return
            
            matching_bins = search_bins_in_csv(search_prefix)
            
            if not matching_bins:
                await callback_query.answer("No BINs found!", show_alert=True)
                return
            
            bins_per_page = 3
            total_pages = (len(matching_bins) + bins_per_page - 1) // bins_per_page
            
            if action == "next":
                current_page = min(current_page + 1, total_pages - 1)
            elif action == "prev":
                current_page = max(current_page - 1, 0)
            elif action == "exit":
                await callback_query.message.delete()
                await callback_query.answer()
                return
            
            # Get bins for current page
            page_bins = get_bins_for_page(matching_bins, current_page, bins_per_page)
            
            # Format the response
            a_symbol = f"<a href='tg://user?id={user_id}'>ア</a>"
            ki_symbol = f"<a href='tg://user?id={user_id}'>キ</a>"
            ka_symbol = f"<a href='tg://user?id={user_id}'>カ</a>"
            shu_symbol = f"<a href='tg://user?id={user_id}'>朱</a>"
            zero_symbol = f"<a href='tg://user?id={user_id}'>零</a>"
            gen_symbol = f"<a href='tg://user?id={user_id}'>ᥫ᭡</a>"
            user_link = f"<a href='tg://user?id={user_id}'>ª𝗺𝗸𝘂𝘀𝗵</a>"
            
            # Build response
            resp = f"〈{a_symbol}〉𝙎𝙚𝙚𝙙 -» {search_prefix}xxx\n"
            resp += "- - - - - - - - - - - - - - - - - - - - -\n"
            
            for i, bin_info in enumerate(page_bins):
                brand = bin_info.get("brand", "N/A").upper()
                card_type = bin_info.get("type", "N/A").upper()
                level = bin_info.get("level", "N/A").upper()
                bank = bin_info.get("bank_name", "N/A")
                country_code = bin_info.get("country", "N/A")
                flag = bin_info.get("flag", "")
                country_full_name = get_country_name(country_code).upper()
                
                resp += f"〈{ki_symbol}〉𝘽𝙞𝙣 -» {bin_info['bin']}\n"
                resp += f"〈{ka_symbol}〉𝙄𝙣𝙛𝙤 -» {brand} - {card_type} - {level}\n"
                resp += f"〈{shu_symbol}〉𝘽𝙖𝙣𝙠 -» {bank}\n"
                resp += f"〈{zero_symbol}〉𝘾𝙤𝙪𝙣𝙩𝙧y -» {country_full_name} {flag}\n"
                
                if i < len(page_bins) - 1:
                    resp += "- - - - - - - - - - - - - - - - - - - - -\n"
            
            resp += f"- - - - - - - - - - - - - - - - - - - - -\n"
            resp += f"〈{ki_symbol}〉𝙋𝙖𝙜𝙚 -» {current_page + 1}/{total_pages}\n"
            resp += f"- - - - - - - - - - - - - - - - - - - - -\n"
            resp += f"〈{gen_symbol}〉 𝙂𝙚𝙣 𝙗𝙮 -» {user_link}"
            
            # Create keyboard
            keyboard = create_gbin_keyboard(user_id, search_prefix, current_page, total_pages)
            
            await callback_query.message.edit_text(resp, reply_markup=keyboard, disable_web_page_preview=True)
            await callback_query.answer()
        
        except Exception as e:
            await callback_query.answer()
            print(f"Error in gbin callback: {e}")
    
    print("✅ User tools commands registered (/hit, /bin, /gbin)")
