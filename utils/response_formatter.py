def categorize_response(refusal_reason_raw, result_code=None):
    """
    Categorize response based on refusalReasonRaw or resultCode.
    Returns: 'approved', 'declined', or '3ds'
    """
    if not refusal_reason_raw and not result_code:
        return 'declined'
    
    # Use refusalReasonRaw if available, otherwise use resultCode
    text_to_check = (refusal_reason_raw or result_code or '').lower()
    
    # Check for 3DS/Authentication keywords
    auth_keywords = ['3ds', '3d', 'threed', 'RedirectShopper', 'challengeshopper', 'authentication']
    if any(keyword in text_to_check for keyword in auth_keywords):
        return '3ds'
    
    # Check for approval keywords
    approval_keywords = ['cvv', 'cvc', 'insufficient', 'avs', 'approved', 'approve', 
                        'partial', 'approval', 'withdrawal']
    if any(keyword in text_to_check for keyword in approval_keywords):
        return 'approved'
    
    # Default to declined
    return 'declined'

def get_status_emoji(category):
    """Get emoji for status category"""
    emoji_map = {
        'approved': '𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅',
        'declined': '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌',
        '3ds': '𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ❎'
    }
    return emoji_map.get(category, '𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌')

def format_response(card_info, gateway_name, response_message, bin_info, execution_time, 
                   refusal_reason_raw=None, result_code=None, merchant_advice_code=None):
    """
    Format the response message for Telegram.
    
    Args:
        card_info: tuple (card, month, year, cvv)
        gateway_name: str - name of the gateway
        response_message: str - main response/error message
        bin_info: dict - BIN information
        execution_time: float - time taken in seconds
        refusal_reason_raw: str - optional refusal reason
        result_code: str - optional result code (used if refusal_reason_raw is None)
        merchant_advice_code: str - optional merchant advice code
    
    Returns:
        str - formatted message
    """
    card, month, year, cvv = card_info
    cc_display = f"`{card}|{month}|{year}|{cvv}`"
    
    # Determine status category
    category = categorize_response(refusal_reason_raw, result_code)
    status_text = get_status_emoji(category)
    
    # Build response message
    # Use refusalReasonRaw if available, otherwise use resultCode
    main_response = refusal_reason_raw if refusal_reason_raw else result_code
    
    response_text = f"{status_text}\n\n"
    response_text += f"[㊕](t.me/spid_3r) 𝗖𝗖 ⇾ {cc_display}\n"
    response_text += f"[㊕](t.me/spid_3r) 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ {gateway_name}\n"
    
    # Add response with merchant advice code if present
    if merchant_advice_code:
        response_text += f"[㊕](t.me/spid_3r) 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {main_response} ⇾ {merchant_advice_code}\n\n"
    else:
        response_text += f"[㊕](t.me/spid_3r) 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {main_response}\n\n"
    
    # Add BIN info if available
    if bin_info:
        response_text += f"[㊕](t.me/spid_3r) 𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('vendor', 'N/A')} - {bin_info.get('type', 'N/A')} - {bin_info.get('level', 'N/A')}\n"
        response_text += f"[㊕](t.me/spid_3r) 𝗕𝗮𝗻𝗸: {bin_info.get('bank_name', 'N/A')}\n"
        response_text += f"[㊕](t.me/spid_3r) 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'N/A')} {bin_info.get('flag', '')}\n\n"
    
    response_text += f"[㊕](t.me/spid_3r) 𝗧𝗼𝗼𝗸 {execution_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀"
    
    return response_text

def get_response_keyboard():
    """Get the standard response keyboard with buttons"""
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = [
        [
            InlineKeyboardButton("𝗖𝗛𝗔𝗡𝗡𝗘𝗟", url="https://t.me/migeldumps"),
            InlineKeyboardButton("𝗢𝗪𝗡𝗘𝗥", url="https://t.me/spid_3r")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
