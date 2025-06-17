import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        # Load from .env file or environment variables
        self.token = os.getenv('DISCORD_TOKEN')
        self.minefort_email = os.getenv('MINEFORT_EMAIL')
        self.minefort_password = os.getenv('MINEFORT_PASSWORD')
        self.server_ip = os.getenv('MINECRAFT_SERVER_IP', 'fcksociety.minefort.com')
        
        # Channel IDs
        self.cpanel_channel_id = int(os.getenv('CPANEL_CHANNEL_ID', '0'))
        self.commands_channel_id = int(os.getenv('COMMANDS_CHANNEL_ID', '0'))
        
        # Role IDs
        self.admin_role_id = int(os.getenv('ADMIN_ROLE_ID', '0'))
        self.mod_role_id = int(os.getenv('MOD_ROLE_ID', '0'))
        
        # Voice channel category/channel IDs
        self.temp_vc_category_id = int(os.getenv('TEMP_VC_CATEGORY_ID', '0'))
        self.create_vc_channel_id = int(os.getenv('CREATE_VC_CHANNEL_ID', '0'))

    def save_config(self):
        """Save configuration to config.json"""
        config_dict = {
            "server_ip": self.server_ip,
            "cpanel_channel_id": self.cpanel_channel_id,
            "commands_channel_id": self.commands_channel_id,
            "admin_role_id": self.admin_role_id,
            "mod_role_id": self.mod_role_id,
            "temp_vc_category_id": self.temp_vc_category_id,
            "create_vc_channel_id": self.create_vc_channel_id
        }
        
        with open('config.json', 'w') as f:
            json.dump(config_dict, f, indent=4)

    def load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                
                # Update attributes
                for key, value in config.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                        
        except FileNotFoundError:
            # Create default config
            self.save_config()
        except json.JSONDecodeError:
            print("Error: config.json is invalid. Using default values.")

config = Config()
config.load_config()