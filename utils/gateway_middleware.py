"""
Gateway Middleware
Handles pre-processing validation before gateway calls
"""

from utils.card_utils import validate_card_number
from utils.bin_lookup import get_bin_info
from utils.response_formatter import get_response_keyboard
from pyrogram.enums import ParseMode

async def validate_card_with_luhn(card_info, gateway_name, message):
    """
    Validate card using Luhn algorithm
    Returns True if valid, False if invalid (and sends error response)
    """
    if not card_info:
        return False
    
    card, month, year, cvv = card_info
    
    # Luhn validation
    if not validate_card_number(card):
        # Get BIN info for display
        bin_info = get_bin_info(card)
        
        # Format error response
        cc_display = f"`{card}|{month}|{year}|{cvv}`"
        
        response_text = f"𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌\n\n"
        response_text += f"㊕ 𝗖𝗖 ⇾ {cc_display}\n"
        response_text += f"㊕ 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ {gateway_name}\n"
        response_text += f"㊕ 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ Invalid card number (F)\n\n"
        
        # Add BIN info if available
        if bin_info:
            response_text += f"㊕ 𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('vendor', 'N/A')} - {bin_info.get('type', 'N/A')} - {bin_info.get('level', 'N/A')}\n"
            response_text += f"㊕ 𝗕𝗮𝗻𝗸: {bin_info.get('bank_name', 'N/A')}\n"
            response_text += f"㊕ 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'N/A')} {bin_info.get('flag', '')}\n\n"
        
        response_text += f"㊕ 𝗧𝗼𝗼𝗸 0.01 𝘀𝗲𝗰𝗼𝗻𝗱𝘀"
        
        keyboard = get_response_keyboard()
        await message.reply_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
        return False
    
    return True