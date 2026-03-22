import csv
import os

BIN_CACHE = {}
BIN_FILE = "bins_all.csv"

def load_bin_database():
    """Load BIN database from CSV file"""
    global BIN_CACHE
    
    if not os.path.exists(BIN_FILE):
        print(f"⚠️ Warning: BIN database file '{BIN_FILE}' not found")
        return
    
    try:
        with open(BIN_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 7:
                    bin_number = row[0].strip().strip('"')
                    BIN_CACHE[bin_number] = {
                        'country': row[1].strip().strip('"'),
                        'flag': row[2].strip().strip('"'),
                        'vendor': row[3].strip().strip('"'),
                        'type': row[4].strip().strip('"'),
                        'level': row[5].strip().strip('"'),
                        'bank_name': row[6].strip().strip('"')
                    }
        print(f"✅ Loaded {len(BIN_CACHE)} BINs from database")
    except Exception as e:
        print(f"❌ Error loading BIN database: {e}")

def get_bin_info(card_number):
    """
    Get BIN information for a card number.
    Returns dict with bin info or None if not found.
    """
    if not BIN_CACHE:
        load_bin_database()
    
    if not card_number:
        return None
    
    # Try BIN lengths from longest to shortest (6 digits is standard)
    for bin_length in [8, 6]:
        bin_number = card_number[:bin_length]
        if bin_number in BIN_CACHE:
            return BIN_CACHE[bin_number]
    
    return None

def format_bin_info(bin_info):
    """Format BIN info for display"""
    if not bin_info:
        return "N/A"
    
    vendor = bin_info.get('vendor', 'N/A')
    card_type = bin_info.get('type', 'N/A')
    level = bin_info.get('level', 'N/A')
    bank = bin_info.get('bank_name', 'N/A')
    country = bin_info.get('country', 'N/A')
    flag = bin_info.get('flag', '')
    
    return {
        'vendor': vendor,
        'type': card_type,
        'level': level,
        'bank_name': bank,
        'country': country,
        'flag': flag
    }

# Load BIN database on module import
load_bin_database()
