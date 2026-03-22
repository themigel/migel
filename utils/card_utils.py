import re

# Card regex patterns for extraction
CARD_PATTERNS = [
    # Standard format: 1234567890123456|12|2027|123
    r'(\d{13,19})\s*[\|\/\:]\s*(\d{1,2})\s*[\|\/\:]\s*(\d{2,4})\s*[\|\/\:]\s*(\d{3,4})',
    
    # With spaces in card number: 1234 5678 9012 3456|12|2027|123
    r'(\d{4}\s*\d{4}\s*\d{4}\s*\d{3,4})\s*[\|\/\:]\s*(\d{1,2})\s*[\|\/\:]\s*(\d{2,4})\s*[\|\/\:]\s*(\d{3,4})',
    
    # Slash separator: 1234567890123456/12/2027/123
    r'(\d{13,19})\s*\/\s*(\d{1,2})\s*\/\s*(\d{2,4})\s*\/\s*(\d{3,4})',
    
    # Colon separator: 1234567890123456:12:2027:123
    r'(\d{13,19})\s*\:\s*(\d{1,2})\s*\:\s*(\d{2,4})\s*\:\s*(\d{3,4})',
    
    # Space separator: 1234567890123456 12 2027 123
    r'(\d{13,19})\s+(\d{1,2})\s+(\d{2,4})\s+(\d{3,4})',
    
    # With text labels: Card: 1234567890123456 Exp: 12/27 CVV: 123
    r'(?:card|cc|number)?[\s\:]*(\d{13,19})[\s\,]*(?:exp|expiry|date)?[\s\:]*(\d{1,2})\s*[\/\-]\s*(\d{2,4})[\s\,]*(?:cvv|cvc|security)?[\s\:]*(\d{3,4})',
]

def extract_card_info(text):
    """
    Extract card information from text using multiple regex patterns.
    Returns tuple: (card_number, month, year, cvv) or None if not found
    """
    if not text:
        return None
    
    text = text.strip()
    
    for pattern in CARD_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) >= 4:
                card = groups[0].replace(' ', '')  # Remove spaces from card number
                month = groups[1].zfill(2)  # Ensure 2 digits
                year = groups[2]
                cvv = groups[3]
                
                # Normalize year to 4 digits
                if len(year) == 2:
                    year = '20' + year
                
                # Validate basic card number length
                if 13 <= len(card) <= 19:
                    return (card, month, year, cvv)
    
    return None

def format_card_display(card, month, year, cvv):
    """Format card info for display: 1234567890123456|12|2027|123"""
    return f"{card}|{month}|{year}|{cvv}"

def validate_card_number(card_number):
    """Validate card number using Luhn algorithm"""
    card_number = card_number.replace(' ', '')
    
    if not card_number.isdigit():
        return False
    
    if len(card_number) < 13 or len(card_number) > 19:
        return False
    
    # Luhn algorithm
    def luhn_checksum(card_num):
        def digits_of(n):
            return [int(d) for d in str(n)]
        digits = digits_of(card_num)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d*2))
        return checksum % 10
    
    return luhn_checksum(card_number) == 0
