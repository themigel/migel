"""
Database module for bot user management
Handles users, premium access, bans, and statistics
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List

DB_FILE = "bot_database.json"

class Database:
    def __init__(self):
        self.data = self.load_database()
    
    def load_database(self):
        """Load database from JSON file"""
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r') as f:
                    return json.load(f)
            except:
                return self.get_default_structure()
        return self.get_default_structure()
    
    def get_default_structure(self):
        """Get default database structure"""
        return {
            "users": {},
            "stats": {
                "total_checks": 0,
                "total_users": 0,
                "checks_by_gateway": {}
            },
            "settings": {
                "maintenance": False,
                "forward_to_admin": False,
                "locked_gateways": []
            },
            "premium_gateways": []
        }
    
    def save_database(self):
        """Save database to JSON file"""
        try:
            with open(DB_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving database: {e}")
            return False
    
    def add_user(self, user_id: int, username: str = None):
        """Add or update user"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.data["users"]:
            self.data["users"][user_id_str] = {
                "user_id": user_id,
                "username": username,
                "joined_date": datetime.now().isoformat(),
                "total_checks": 0,
                "is_banned": False,
                "is_premium": False,
                "premium_until": None,
                "last_check": None
            }
            self.data["stats"]["total_users"] += 1
        else:
            # Update username if provided
            if username:
                self.data["users"][user_id_str]["username"] = username
        
        self.save_database()
        return self.data["users"][user_id_str]
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data"""
        return self.data["users"].get(str(user_id))
    
    def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        user = self.get_user(user_id)
        return user.get("is_banned", False) if user else False
    
    def ban_user(self, user_id: int):
        """Ban a user"""
        user_id_str = str(user_id)
        if user_id_str in self.data["users"]:
            self.data["users"][user_id_str]["is_banned"] = True
            self.save_database()
            return True
        return False
    
    def unban_user(self, user_id: int):
        """Unban a user"""
        user_id_str = str(user_id)
        if user_id_str in self.data["users"]:
            self.data["users"][user_id_str]["is_banned"] = False
            self.save_database()
            return True
        return False
    
    def add_premium(self, user_id: int, duration_str: str):
        """
        Add premium access to user
        duration_str format: "30d" (days), "12h" (hours)
        """
        user_id_str = str(user_id)
        if user_id_str not in self.data["users"]:
            return False, "User not found"
        
        # Parse duration
        try:
            if duration_str.endswith('d'):
                days = int(duration_str[:-1])
                expiry = datetime.now() + timedelta(days=days)
            elif duration_str.endswith('h'):
                hours = int(duration_str[:-1])
                expiry = datetime.now() + timedelta(hours=hours)
            else:
                return False, "Invalid duration format. Use: 30d or 12h"
        except:
            return False, "Invalid duration format"
        
        self.data["users"][user_id_str]["is_premium"] = True
        self.data["users"][user_id_str]["premium_until"] = expiry.isoformat()
        self.save_database()
        
        return True, expiry
    
    def is_premium(self, user_id: int) -> bool:
        """Check if user has active premium"""
        user = self.get_user(user_id)
        if not user or not user.get("is_premium"):
            return False
        
        premium_until = user.get("premium_until")
        if not premium_until:
            return False
        
        try:
            expiry = datetime.fromisoformat(premium_until)
            if datetime.now() > expiry:
                # Premium expired
                user["is_premium"] = False
                self.save_database()
                return False
            return True
        except:
            return False
    
    def increment_check(self, user_id: int, gateway: str):
        """Increment check counter"""
        user_id_str = str(user_id)
        if user_id_str in self.data["users"]:
            self.data["users"][user_id_str]["total_checks"] += 1
            self.data["users"][user_id_str]["last_check"] = datetime.now().isoformat()
        
        self.data["stats"]["total_checks"] += 1
        
        if gateway not in self.data["stats"]["checks_by_gateway"]:
            self.data["stats"]["checks_by_gateway"][gateway] = 0
        self.data["stats"]["checks_by_gateway"][gateway] += 1
        
        self.save_database()
    
    def get_stats(self) -> Dict:
        """Get bot statistics"""
        return self.data["stats"]
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        return list(self.data["users"].values())
    
    def set_maintenance(self, status: bool):
        """Set maintenance mode"""
        self.data["settings"]["maintenance"] = status
        self.save_database()
    
    def is_maintenance(self) -> bool:
        """Check if in maintenance mode"""
        return self.data["settings"].get("maintenance", False)
    
    def set_forward_to_admin(self, status: bool):
        """Set forward to admin mode"""
        self.data["settings"]["forward_to_admin"] = status
        self.save_database()
    
    def is_forward_to_admin(self) -> bool:
        """Check if forwarding to admin"""
        return self.data["settings"].get("forward_to_admin", False)
    
    def lock_gateway(self, gateway: str):
        """Lock a gateway"""
        if gateway not in self.data["settings"]["locked_gateways"]:
            self.data["settings"]["locked_gateways"].append(gateway)
            self.save_database()
    
    def unlock_gateway(self, gateway: str):
        """Unlock a gateway"""
        if gateway in self.data["settings"]["locked_gateways"]:
            self.data["settings"]["locked_gateways"].remove(gateway)
            self.save_database()
    
    def is_gateway_locked(self, gateway: str) -> bool:
        """Check if gateway is locked"""
        return gateway in self.data["settings"].get("locked_gateways", [])
    
    def add_premium_gateway(self, gateway: str):
        """Make gateway premium-only"""
        if gateway not in self.data["premium_gateways"]:
            self.data["premium_gateways"].append(gateway)
            self.save_database()
    
    def remove_premium_gateway(self, gateway: str):
        """Remove gateway from premium-only"""
        if gateway in self.data["premium_gateways"]:
            self.data["premium_gateways"].remove(gateway)
            self.save_database()
    
    def is_gateway_premium(self, gateway: str) -> bool:
        """Check if gateway requires premium"""
        return gateway in self.data.get("premium_gateways", [])

# Global database instance
db = Database()
