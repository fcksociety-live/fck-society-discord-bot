import requests
import time
from typing import Dict, List, Any, Optional, Tuple
import json

class MinefortAPI:
    """Wrapper for Minefort API to manage Minecraft servers."""
    
    BASE_URL = "https://api.minefort.com/v1"
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.is_logged_in = False
        self.last_console_log = ""
    
    def login(self) -> bool:
        """Log in to the Minefort API."""
        login_endpoint = f"{self.BASE_URL}/auth/login"
        
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://minefort.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }
        
        payload = {
            "emailAddress": self.email,
            "password": self.password
        }

        try:
            response = self.session.post(login_endpoint, headers=headers, json=payload)
            response.raise_for_status()
            self.is_logged_in = True
            return True

        except Exception as e:
            print(f"❌ Login failed: {str(e)}")
            self.is_logged_in = False
            return False
    
    def ensure_login(self) -> bool:
        """Ensure that the user is logged in, attempting login if necessary."""
        if not self.is_logged_in:
            return self.login()
        return True
    
    def get_servers(self) -> List[Dict[str, Any]]:
        """Get the list of user's servers."""
        if not self.ensure_login():
            return []
            
        servers_endpoint = f"{self.BASE_URL}/user/servers"
        
        headers = {
            "accept": "application/json, text/plain, */*",
            "origin": "https://minefort.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

        try:
            response = self.session.get(servers_endpoint, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get('result', [])
        except Exception as e:
            # Try to re-login if the session might have expired
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code in [401, 403]:
                self.is_logged_in = False
                if self.login():
                    return self.get_servers()  # Retry after login
            return []
    
    def perform_server_action(self, server_id: str, action: str) -> Tuple[bool, str]:
        """
        Perform an action on a server.
        
        Args:
            server_id: The ID of the server
            action: One of 'start', 'kill', 'sleep', 'wakeup'
            
        Returns:
            Tuple of (success, message)
        """
        if not self.ensure_login():
            return False, "Failed to login to Minefort"
            
        valid_actions = {'start', 'kill', 'sleep', 'wakeup'}
        if action not in valid_actions:
            return False, f"Invalid action. Must be one of: {', '.join(valid_actions)}"
            
        action_endpoint = f"{self.BASE_URL}/server/{server_id}/{action}"
        
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-length": "0",
            "origin": "https://minefort.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

        try:
            response = self.session.post(action_endpoint, headers=headers)
            response.raise_for_status()
            
            # Parse response
            json_response = response.json()
            
            # Check for success indicators in the response
            if response.status_code == 200:
                action_name = action.replace('wakeup', 'wake up')
                return True, f"Server {action_name} request sent successfully"
            else:
                return False, json_response.get('message', 'Unknown error occurred')
                
        except Exception as e:
            # Try to re-login if the session might have expired
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code in [401, 403]:
                self.is_logged_in = False
                if self.login():
                    return self.perform_server_action(server_id, action)  # Retry after login
                    
            return False, f"Error performing action: {str(e)}"

    def get_console_logs(self, server_id: str) -> Tuple[bool, str]:
        """
        Get console logs for a server.
        
        Args:
            server_id: The ID of the server
            
        Returns:
            Tuple of (success, logs)
        """
        if not self.ensure_login():
            return False, "Failed to login to Minefort"
            
        # Try the console endpoint
        console_endpoint = f"{self.BASE_URL}/server/{server_id}/console"
        
        headers = {
            "accept": "application/json, text/plain, */*",
            "origin": "https://minefort.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

        try:
            response = self.session.get(console_endpoint, headers=headers)
            response.raise_for_status()
            
            json_response = response.json()
            logs = json_response.get('logs', json_response.get('result', json_response.get('console', '')))
            
            return True, logs
                
        except Exception as e:
            return False, f"Error fetching console logs: {str(e)}"

    def send_console_command(self, server_id: str, command: str) -> Tuple[bool, str]:
        """
        Send a command to the server console.
        
        Args:
            server_id: The ID of the server
            command: The command to send
            
        Returns:
            Tuple of (success, message)
        """
        if not self.ensure_login():
            return False, "Failed to login to Minefort"
            
        # Use the correct endpoint /command
        command_endpoint = f"{self.BASE_URL}/server/{server_id}/command"
        
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://minefort.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }
        
        payload = {
            "command": command
        }

        try:
            response = self.session.post(command_endpoint, headers=headers, json=payload)
            response.raise_for_status()
            
            return True, f"Command '{command}' sent successfully"
                
        except Exception as e:
            return False, f"Error sending command: {str(e)}"

    def get_status_message(self, server) -> str:
        """Get a formatted status message for a server."""
        status_text = "UNKNOWN"
        
        # Map state codes to status messages
        if 'state' in server:
            state_map = {
                0: "HIBERNATING",
                1: "PROCESSING",
                3: "STARTING",
                4: "RUNNING",
                5: "OFFLINE",
                8: "STOPPING"
            }
            status_text = state_map.get(server['state'], f"UNKNOWN (State {server['state']})")
        
        return f"{server.get('serverName', 'Unknown')} - Status: {status_text}"
    
    def get_player_list(self, server_id: str) -> Tuple[bool, List[str], str]:
        """
        Get the list of online players for a server.
        
        Returns:
            Tuple of (success, [player_names], message)
        """
        # Find the server in the list
        servers = self.get_servers()
        target_server = next((s for s in servers if s.get('serverId') == server_id), None)
        
        if not target_server:
            return False, [], "Server not found"
            
        # Check if server is running
        if target_server.get('state') != 4:  # 4 = RUNNING
            status = self.get_status_message(target_server)
            return False, [], f"Server is not running. Current status: {status}"
            
        # If server is running, get the player list from the server details
        player_list = target_server.get('players', [])
        if isinstance(player_list, list):
            return True, player_list, f"{len(player_list)} players online"
        else:
            return True, [], "0 players online"
