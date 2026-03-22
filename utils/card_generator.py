"""
Card Generator Module
Contains /gen command with Luhn validation, regen, and file generation
"""

import os
import time
import random
import re
import asyncio
import threading
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# Import from utils
from utils.card_utils import validate_card_number

# BIN data (shared with user_tools)
from utils.user_tools import bin_data_cache, get_country_name, get_bin_info_from_csv

# Regen cooldown tracker
regen_cooldown = {}

def clean_bin_input(bin_input):
    """Clean and extract just the BIN part from various inputs"""
    clean_bin = re.sub(r'\D', '', bin_input)
    return clean_bin

def is_valid_bin(bin_code):
    """Check if BIN exists in our database"""
    # Check exact match
    if bin_code in bin_data_cache:
        return True
    
    # Check partial matches (shorter BINs)
    for length in range(len(bin_code)-1, 4, -1):
        partial_bin = bin_code[:length]
        if partial_bin in bin_data_cache:
            return True
    
    return False

async def cc_generator(cc, mes, ano, cvv):
    """
    Generate a single card with given parameters
    Preserves all given digits (important!)
    """
    cc, mes, ano, cvv = str(cc), str(mes), str(ano), str(cvv)
    
    # Clean the BIN input but preserve all given digits
    clean_cc = clean_bin_input(cc)
    
    # Handle month - ensure proper format
    if mes == "None" or 'X' in mes or 'x' in mes or 'rnd' in mes or not mes.isdigit():
        mes = str(random.randint(1, 12))
        if len(mes) == 1:
            mes = "0" + mes
    elif mes != "None" and len(mes) == 1:
        mes = "0" + mes
    elif len(mes) > 2:
        mes = mes[:2]
    
    # Handle year - ensure proper format
    if ano == "None" or 'X' in ano or 'x' in ano or 'rnd' in ano or not ano.isdigit():
        ano = str(random.randint(2024, 2035))
    elif ano != "None" and len(ano) == 2:
        ano = "20" + ano
    elif len(ano) > 4:
        ano = ano[:4]
    
    # Determine card type and length based on given BIN
    is_amex = clean_cc.startswith(('34', '37'))
    
    if is_amex:
        card_length = 15
        cvv_length = 4
    else:
        card_length = 16
        cvv_length = 3
    
    # Generate only the remaining digits needed
    numbers = list("0123456789")
    random.shuffle(numbers)
    random_digits = "".join(numbers)
    
    # Calculate how many digits we need to generate
    digits_needed = card_length - len(clean_cc)
    if digits_needed > 0:
        cc_result = clean_cc + random_digits[:digits_needed]
    else:
        cc_result = clean_cc[:card_length]
    
    # Handle CVV - ensure proper format
    if cvv == "None" or 'x' in cvv or 'X' in cvv or 'rnd' in cvv or not cvv.isdigit():
        if is_amex:
            cvv_result = str(random.randint(1000, 9999))
        else:
            cvv_result = str(random.randint(100, 999))
    else:
        clean_cvv = re.sub(r'\D', '', cvv)
        if is_amex:
            cvv_result = clean_cvv[:4] if len(clean_cvv) >= 4 else str(random.randint(1000, 9999))
        else:
            cvv_result = clean_cvv[:3] if len(clean_cvv) >= 3 else str(random.randint(100, 999))
    
    return f"{cc_result}|{mes}|{ano}|{cvv_result}"

async def luhn_card_generator(cc, mes, ano, cvv, amount):
    """Generate multiple cards with Luhn validation"""
    all_cards = ""
    for _ in range(amount):
        while True:
            result = await cc_generator(cc, mes, ano, cvv)
            ccx, mesx, anox, cvvx = result.split("|")
            
            # Validate with Luhn
            if validate_card_number(ccx):
                all_cards += f"{ccx}|{mesx}|{anox}|{cvvx}\n"
                break
    
    return all_cards

def encode_params_simple(cc, mes, ano, cvv, amount, user_id):
    """Simple encoding with user ID for callback data"""
    clean_cc = clean_bin_input(cc)
    clean_mes = mes[:2] if mes != "None" else "00"
    clean_ano = ano[:4] if ano != "None" else "0000"
    clean_cvv = cvv[:4] if cvv != "None" else "0000"
    
    return f"{clean_cc}|{clean_mes}|{clean_ano}|{clean_cvv}|{amount}|{user_id}"

def decode_params_simple(encoded_params):
    """Decode simple encoded parameters"""
    try:
        parts = encoded_params.split("|")
        if len(parts) != 6:
            return None
        
        cc, mes, ano, cvv, amount, user_id = parts
        
        # Convert back to original format
        mes = mes if mes != "00" else "None"
        ano = ano if ano != "0000" else "None"
        cvv = cvv if cvv != "0000" else "None"
        amount = int(amount)
        
        return {
            'cc': cc,
            'mes': mes,
            'ano': ano,
            'cvv': cvv,
            'amount': amount,
            'user_id': user_id
        }
    except:
        return None

def extract_bin_from_reply(message):
    """Extract BIN from replied message text"""
    if not message.reply_to_message or not message.reply_to_message.text:
        return None
    
    text = message.reply_to_message.text
    patterns = [
        r'(\d{6,19})(?:\||\s|$)',
        r'(\d{6,19}\|\d{1,2})',
        r'(\d{6,19}\|\d{1,2}\|\d{2,4})',
        r'(\d{6,19}\|\d{1,2}\|\d{2,4}\|\d{3,4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

def generate_response(cc, amount, all_cards, brand, type_, level, bank, country, flag, time_taken, user_name, user_id):
    """Generate formatted response for card generation"""
    cards_list = all_cards.strip().split('\n')
    cards_block = "\n".join([f"<code>{card}</code>" for card in cards_list])
    
    return f"""
- 𝐂𝐂 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲
- 𝐁𝐢𝐧 - {cc}
- 𝐀𝐦𝐨𝐮𝐧𝐭 - {amount}
⋆——————✰◦✰◦✰——————⋆
{cards_block}
⋆——————✰◦✰◦✰——————⋆
- 𝗜𝗻𝗳𝗼 - {brand} - {type_} - {level}
- 𝐁𝐚𝐧𝐤 - {bank} 🏛
- 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 - {country} - {flag}

- 𝐓𝐢𝐦𝐞: - {time_taken:0.2f} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬
𝗚𝗲𝗻 𝗯𝘆 :  <a href="tg://user?id={user_id}"> {user_name}</a>
𝗢𝘄𝗻𝗲𝗿 :  <a href="https://t.me/amkuushu">&#8203;ッ</a>
"""

def setup_card_generator(app: Client):
    """Setup card generator command"""
    
    @app.on_message(filters.command(["gen"], prefixes=[".", "/"]))
    def multi(client, message):
        """Thread wrapper for async gen command"""
        t1 = threading.Thread(target=bcall, args=(client, message))
        t1.start()
    
    def bcall(client, message):
        """Async event loop wrapper"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(gen_cmd(client, message))
        loop.close()
    
    async def gen_cmd(client, message):
        """Main gen command handler"""
        try:
            user_id = str(message.from_user.id)
            user_name = message.from_user.first_name
            
            # Check if this is a reply to a message
            ccsdata = None
            if message.reply_to_message:
                ccsdata = extract_bin_from_reply(message)
            
            # If not a reply or couldn't extract from reply, use command arguments
            if not ccsdata:
                try:
                    ccsdata = message.text.split()[1]
                except IndexError:
                    # Format error message
                    resp = f"""
<a href='tg://user?id={user_id}'>〈〆〉</a>𝗦𝗸1𝗺𝗺𝗲𝗿 𝗮𝗹𝗴𝗼 -»>_

<a href='tg://user?id={user_id}'>〈北〉</a>Extra Invalid! ⚠

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /gen 400022|10|2028
"""
                    await message.reply_text(resp)
                    return
            
            # Parse the BIN data
            cc_parts = ccsdata.split("|")
            cc = cc_parts[0]
            mes = cc_parts[1] if len(cc_parts) > 1 else "None"
            ano = cc_parts[2] if len(cc_parts) > 2 else "None"
            cvv = cc_parts[3] if len(cc_parts) > 3 else "None"
            
            # Clean and validate BIN
            clean_cc = clean_bin_input(cc)
            if not is_valid_bin(clean_cc[:6]):
                resp = f"""
<a href='tg://user?id={user_id}'>(〆)</a> 𝗡𝗶𝗰𝗲 𝘁𝗿𝘆 𝗯𝘂𝗱𝗱𝘆.....
   
:(

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗯𝗶𝗻 ⚠️
"""
                await message.reply_text(resp)
                return
            
            amount = 10  # Default amount
            try:
                amount = int(message.text.split()[2])
            except (IndexError, ValueError):
                pass
            
            # Check amount limit BEFORE sending "Generating..." message
            if amount > 10000:
                resp = """<b>Limit Reached ⚠️

Message: Maximum Generated Amount is 10K.</b>"""
                await message.reply_text(resp)
                return
            
            delete = await message.reply_text("<b>Generating...</b>")
            start = time.perf_counter()
            
            # Get BIN details
            bin_info = get_bin_info_from_csv(clean_cc[:6])
            if bin_info:
                brand = bin_info.get("brand", "N/A").upper()
                type_ = bin_info.get("type", "N/A").upper()
                level = bin_info.get("level", "N/A").upper()
                bank = bin_info.get("bank_name", "N/A")
                country_code = bin_info.get("country", "N/A")
                flag = bin_info.get("flag", "")
                country = get_country_name(country_code).upper()
            else:
                brand = type_ = level = bank = country = "N/A"
                flag = ""
            
            # Generate cards
            all_cards = await luhn_card_generator(cc, mes, ano, cvv, amount)
            time_taken = time.perf_counter() - start
            
            # Encode parameters for regen callback
            encoded_params = encode_params_simple(cc, mes, ano, cvv, amount, user_id)
            
            # Check if callback data is within Telegram limits (64 bytes)
            if len(f"regen_{encoded_params}") > 64:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("𝗗𝗼𝗻'𝘁 𝗽𝗿𝗲𝘀𝘀 🤧", callback_data="dontpress_button")],
                    [InlineKeyboardButton("𝗘𝘅𝗶𝘁 ⚠️", callback_data=f"exit_gen_{user_id}")]
                ])
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("𝗥𝗲𝗴𝗲𝗻", callback_data=f"regen_{encoded_params}")],
                    [InlineKeyboardButton("𝗗𝗼𝗻'𝘁 𝗽𝗿𝗲𝘀𝘀 🤧", callback_data="dontpress_button")],
                    [InlineKeyboardButton("𝗘𝘅𝗶𝘁 ⚠️", callback_data=f"exit_gen_{user_id}")]
                ])
            
            if amount <= 10:
                response_text = generate_response(
                    cc, amount, all_cards, brand, type_, level, bank,
                    country, flag, time_taken, user_name, user_id
                )
                
                await client.delete_messages(message.chat.id, delete.id)
                await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
            else:
                # Generate file for bulk
                filename = f"{amount}x_CC_Generated_By_{user_id}.txt"
                with open(filename, "w") as f:
                    f.write(all_cards)
                
                caption = f"""
- 𝐁𝐢𝐧: <code>{cc}</code> 
- 𝐀𝐦𝐨𝐮𝐧𝐭: {amount}

- 𝗜𝗻𝗳𝗼 - {brand} - {type_} - {level}
- 𝐁𝐚𝐧𝐤 - {bank} 🏛  
- 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 - {country} - {flag}

- 𝐓𝐢𝐦𝐞 - {time_taken:0.2f} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬
𝗚𝗲𝗻 𝗯𝘆 :  <a href="tg://user?id={user_id}"> {user_name}</a>
𝗢𝘄𝗻𝗲𝗿 :  <a href="https://t.me/Migel_aktz">&#8203;ッ</a>
"""
                await client.delete_messages(message.chat.id, delete.id)
                await message.reply_document(
                    document=filename,
                    caption=caption,
                    reply_to_message_id=message.id
                )
                os.remove(filename)
        
        except Exception as e:
            import traceback
            print(f"Error in gen command: {traceback.format_exc()}")
            try:
                await client.delete_messages(message.chat.id, delete.id)
            except:
                pass
            await message.reply_text("An error occurred while processing your request.")
    
    # Callback handlers for gen
    @app.on_callback_query(filters.regex("^(regen_|exit_gen_|dontpress_)"))
    async def handle_gen_callback(client, callback_query):
        """Handle gen command callbacks"""
        try:
            # Handle the "Don't press" button
            if callback_query.data == "dontpress_button":
                await callback_query.answer("( -_•)▄︻デ══━一 * * (- _ -)", show_alert=True)
                return
            
            if callback_query.data.startswith("exit_gen_"):
                data_param = callback_query.data.replace("exit_gen_", "")
                user_id = str(callback_query.from_user.id)
                
                if user_id != data_param:
                    await callback_query.answer("〈Start your own /gen〉\n( -_•)▄︻デ══━一", show_alert=True)
                    return
                
                await callback_query.message.delete()
                await callback_query.answer("Message deleted", show_alert=False)
                return
            
            if callback_query.data.startswith("regen_"):
                action, data_param = callback_query.data.split("_", 1)
                user_id = str(callback_query.from_user.id)
                
                # Check cooldown
                current_time = time.time()
                if user_id in regen_cooldown:
                    time_since_last = current_time - regen_cooldown[user_id]
                    if time_since_last < 2:
                        await callback_query.answer("Please wait a moment...", show_alert=False)
                        return
                
                # Set cooldown
                regen_cooldown[user_id] = current_time
                
                # Decode parameters
                params = decode_params_simple(data_param)
                if not params:
                    await callback_query.answer("Invalid regeneration data!", show_alert=True)
                    return
                
                # Check if user matches
                if user_id != params['user_id']:
                    await callback_query.answer("〈Start your own /gen〉\n( -_•)▄︻デ══━一", show_alert=True)
                    return
                
                # Validate BIN again
                clean_cc = clean_bin_input(params['cc'])
                if not is_valid_bin(clean_cc[:6]):
                    await callback_query.answer("Invalid BIN!", show_alert=True)
                    return
                
                # Acknowledge callback
                await callback_query.answer("Regenerating cards...")
                
                # Generate new cards
                start = time.perf_counter()
                all_cards = await luhn_card_generator(
                    params['cc'], params['mes'], params['ano'], params['cvv'], params['amount']
                )
                time_taken = time.perf_counter() - start
                
                if params['amount'] <= 10:
                    # Get BIN details
                    bin_info = get_bin_info_from_csv(params['cc'][:6])
                    if bin_info:
                        brand = bin_info.get("brand", "N/A").upper()
                        type_ = bin_info.get("type", "N/A").upper()
                        level = bin_info.get("level", "N/A").upper()
                        bank = bin_info.get("bank_name", "N/A")
                        country_code = bin_info.get("country", "N/A")
                        flag = bin_info.get("flag", "")
                        country = get_country_name(country_code).upper()
                    else:
                        brand = type_ = level = bank = country = "N/A"
                        flag = ""
                    
                    response_text = generate_response(
                        params['cc'], params['amount'], all_cards, brand, type_,
                        level, bank, country, flag, time_taken,
                        callback_query.from_user.first_name, callback_query.from_user.id
                    )
                    
                    # Re-encode parameters for next regen
                    new_encoded_params = encode_params_simple(
                        params['cc'], params['mes'], params['ano'], params['cvv'],
                        params['amount'], callback_query.from_user.id
                    )
                    
                    # Check callback data size
                    if len(f"regen_{new_encoded_params}") > 64:
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("𝗗𝗼𝗻'𝘁 𝗽𝗿𝗲𝘀𝘀 🤧", callback_data="dontpress_button")],
                            [InlineKeyboardButton("𝗘𝘅𝗶𝘁 ⚠️", callback_data=f"exit_gen_{callback_query.from_user.id}")]
                        ])
                    else:
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("𝗥𝗲𝗴𝗲𝗻", callback_data=f"regen_{new_encoded_params}")],
                            [InlineKeyboardButton("𝗗𝗼𝗻'𝘁 𝗽𝗿𝗲𝘀𝘀 🤧", callback_data="dontpress_button")],
                            [InlineKeyboardButton("𝗘𝘅𝗶𝘁 ⚠️", callback_data=f"exit_gen_{callback_query.from_user.id}")]
                        ])
                    
                    try:
                        await callback_query.message.edit_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
                    except Exception as edit_error:
                        print(f"Edit failed (non-critical): {edit_error}")
                else:
                    await callback_query.answer("Regen not available for large amounts!", show_alert=True)
        
        except Exception as e:
            import traceback
            print(f"Error in gen callback: {traceback.format_exc()}")
            await callback_query.answer("Error processing request!", show_alert=True)
    
    print("✅ Card generator command registered (/gen)")
