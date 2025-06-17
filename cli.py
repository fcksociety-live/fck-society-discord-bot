import requests
import os
import getpass # For securely getting password input
import time # For slight delays, good practice

# --- Configuration ---
BASE_URL = "https://api.minefort.com/v1"

# Initialize a requests session. This session will automatically handle cookies.
# It's crucial for maintaining session state (like login cookies) across requests.
session = requests.Session()

# Global variables to store user credentials.
# These are used for re-login attempts if cookies expire during script execution.
# --- WARNING: FOR LOCAL TESTING ONLY ---
# DO NOT store sensitive credentials directly in code for production or shared environments.
# Use environment variables, a secure configuration file, or a secrets management service.
user_email_global = "example@gmail.com"  # <--- REPLACE WITH YOUR EMAIL
user_password_global = "123456"      # <--- REPLACE WITH YOUR PASSWORD
# -------------------------------------

# --- Helper Functions ---

def login_minefort(email: str, password: str) -> bool:
    """
    Performs a login request to Minefort's authentication endpoint.
    If successful, the session object will automatically store the
    necessary authentication cookies for subsequent requests.

    Args:
        email (str): The user's Minefort email address.
        password (str): The user's Minefort password.

    Returns:
        bool: True if login was successful, False otherwise.
    """
    login_endpoint = f"{BASE_URL}/auth/login"
    
    # Headers to mimic a web browser request
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en-GB;q=0.9,en;q=0.8,bn;q=0.7",
        "content-type": "application/json", # Crucial for sending JSON body
        "origin": "https://minefort.com",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    }
    
    # JSON payload containing login credentials
    payload = {
        "emailAddress": email,
        "password": password
    }

    print("\nAttempting to log in to Minefort...")
    try:
        # Send the POST request using the global session object
        response = session.post(login_endpoint, headers=headers, json=payload)
        response.raise_for_status() # Raises an HTTPError for 4xx/5xx responses

        print("Successfully logged in.")
        # Optional: Print current cookies in the session for debugging
        # print(f"Cookies after login: {session.cookies.get_dict()}")
        return True

    except requests.exceptions.HTTPError as http_err:
        print(f"Login failed: HTTP error occurred: {http_err}")
        try:
            # Attempt to parse JSON error message from response
            error_details = response.json()
            print(f"Minefort API Error: {error_details.get('message', 'No specific error message.')}")
            if "Incorrect credentials" in str(error_details):
                print("Hint: Please check your email and password.")
            elif "Too Many Requests" in str(error_details):
                print("Hint: You might be rate-limited. Please wait and try again.")
        except requests.exceptions.JSONDecodeError:
            # If response is not JSON, print raw text for debugging
            print(f"Minefort API Error (non-JSON response): {response.text[:200]}...") # Print first 200 chars
        return False
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Login failed: Connection error occurred: {conn_err}")
        print("Hint: Check your internet connection or Minefort service availability.")
        return False
    except requests.exceptions.Timeout as timeout_err:
        print(f"Login failed: Request timed out: {timeout_err}")
        return False
    except Exception as e:
        print(f"Login failed: An unexpected error occurred: {e}")
        return False

def get_user_servers() -> list:
    """
    Fetches the list of the user's Minefort servers and their statuses.
    Includes retry logic with re-login attempts if authentication fails.

    Returns:
        list: A list of dictionaries, where each dictionary represents a server.
              Returns an empty list if unable to retrieve server data.
    """
    servers_endpoint = f"{BASE_URL}/user/servers"
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en-GB;q=0.9,en;q=0.8,bn;q=0.7",
        "origin": "https://minefort.com",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        # The 'Cookie' header is automatically managed by the 'session' object.
        # 'if-none-match' is for caching, not strictly needed for basic functionality.
    }

    print("\nFetching server status...")
    MAX_RETRIES = 2 # Max attempts: initial try + one re-login retry
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(servers_endpoint, headers=headers)
            response.raise_for_status() # Raises HTTPError for 4xx/5xx responses

            servers_data = response.json()
            # Based on your example, the server list is under the 'result' key
            return servers_data.get('result', []) 

        except requests.exceptions.HTTPError as http_err:
            print(f"Failed to fetch server status (Attempt {attempt + 1}): HTTP error occurred: {http_err}")
            print(f"Response Status: {response.status_code}")
            # print(f"Response Text (first 500 chars): {response.text[:500]}...") # Uncomment for deep debugging
            # print(f"Cookies in session: {session.cookies.get_dict()}") # Uncomment for deep debugging

            # If authentication fails and it's not the last retry, attempt to re-login
            if response.status_code in [401, 403] and attempt < MAX_RETRIES - 1:
                print("Authentication seems to have expired or is invalid. Attempting to re-login...")
                session.cookies.clear() # Clear potentially invalid cookies from session
                if login_minefort(user_email_global, user_password_global): 
                    print("Re-login successful. Retrying server status fetch...")
                    continue # Go to the next attempt in the loop
                else:
                    print("Failed to re-login. Cannot proceed with server status fetch.")
                    return [] # Return empty list if re-login fails
            else:
                # For other HTTP errors or after max retries, just return empty list
                return [] 
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred during server status fetch: {conn_err}")
            return []
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred during server status fetch: {timeout_err}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred during server status fetch: {e}")
            return []
    
    print("Maximum retry attempts reached for fetching server status.")
    return []

def perform_server_action(server_id: str, action: str) -> dict:
    """
    Performs a specified action (start, stop, hibernate, wakeup) on a Minefort server.
    Includes retry logic with re-login attempts if authentication fails.

    Args:
        server_id (str): The ID of the Minefort server.
        action (str): The action to perform ('start', 'stop', 'hibernate', 'wakeup').

    Returns:
        dict: A dictionary containing the status ('success' or 'error') and a message.
    """
    action_endpoint = f"{BASE_URL}/server/{server_id}/{action}" 
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en-GB;q=0.9,en;q=0.8,bn;q=0.7",
        "content-length": "0", # Most actions are POST with no body
        "origin": "https://minefort.com",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/50 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    }

    print(f"\nAttempting to {action.replace('wakeup', 'wake up')} server ID: {server_id}...")
    MAX_RETRIES = 2
    for attempt in range(MAX_RETRIES):
        try:
            response = session.post(action_endpoint, headers=headers)
            response.raise_for_status()

            json_response = response.json()
            if response.status_code == 200:
                # Minefort API responses for actions might vary, check common indicators
                if json_response.get("success", False) or \
                   action in json_response.get("message", "").lower() or \
                   "ing" in json_response.get("message", "").lower() or \
                   "ok" in str(json_response).lower(): # Check for 'ok' in any part of response
                    return {"status": "success", "message": f"Server {action.replace('wakeup', 'wake up')} request sent successfully!"}
                else:
                    return {"status": "error", "message": f"Minefort API reported: {json_response.get('message', 'Unknown error.')}"}
            else:
                return {"status": "error", "message": f"Server responded with status {response.status_code}: {response.text[:200]}..."}

        except requests.exceptions.HTTPError as http_err:
            print(f"Failed to perform {action} (Attempt {attempt + 1}): HTTP error occurred: {http_err}")
            print(f"Response Status: {response.status_code}")
            # print(f"Response Text (first 500 chars): {response.text[:500]}...") # Uncomment for deep debugging
            # print(f"Cookies in session: {session.cookies.get_dict()}") # Uncomment for deep debugging

            if response.status_code in [401, 403] and attempt < MAX_RETRIES - 1:
                print("Authentication seems to have expired or is invalid. Attempting to re-login...")
                session.cookies.clear()
                if login_minefort(user_email_global, user_password_global): 
                    print(f"Re-login successful. Retrying {action} action...")
                    continue 
                else:
                    print("Failed to re-login. Cannot perform server action.")
                    return {"status": "error", "message": "Authentication failed and re-login also failed. Check credentials or site status."}
            elif response.status_code == 400:
                # Handle common 400 Bad Request messages for server actions
                error_message = f"Bad request to Minefort API. Response: {response.text[:100]}..."
                if "already running" in response.text.lower() and action == "start":
                    error_message = "Server is already running."
                elif "not running" in response.text.lower() and action == "stop":
                    error_message = "Server is not running."
                elif "already active" in response.text.lower() and action == "wakeup":
                    error_message = "Server is already awake/online."
                elif "not hibernating" in response.text.lower() and action == "hibernate":
                    error_message = "Server is not in a state to hibernate."
                return {"status": "error", "message": error_message}
            else:
                return {"status": "error", "message": f"HTTP error: {http_err}. Response: {response.text[:200]}..."}
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred during {action}: {conn_err}")
            return {"status": "error", "message": "Could not connect to Minefort API."}
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred during {action}: {timeout_err}")
            return {"status": "error", "message": "Minefort API request timed out."}
        except Exception as e:
            print(f"An unexpected error occurred during {action}: {e}")
            return {"status": "error", "message": f"An unexpected error occurred: {e}"}
    
    return {"status": "error", "message": f"Maximum retry attempts reached for server {action}."}


# --- Main Script Logic ---
if __name__ == "__main__":
    print("--- Minefort Server Manager CLI ---")
    print("This tool allows you to log in to Minefort and manage your Minecraft servers.")
    print("\nWARNING: For local testing only. Credentials are hardcoded in the script.")
    print("DO NOT use this script in production or share it without securing your credentials!")
    
    # Use hardcoded credentials for local testing
    # user_email_input and user_password_input are removed.
    # The global variables user_email_global and user_password_global are used directly.

    # Attempt initial login
    if not login_minefort(user_email_global, user_password_global):
        print("Initial login failed. Please check your hardcoded credentials and try again.")
        exit()

    while True:
        # Fetch and display server status
        servers = get_user_servers()
        
        if not servers:
            print("\nCould not retrieve server list. This might happen if there are no servers associated with your account, or due to an API issue.")
            print("Please ensure your account has servers on Minefort.com.")
        else:
            print("\n--- Your Minefort Servers ---")
            for i, server in enumerate(servers):
                status_color = ""
                status_text = "UNKNOWN"
                
                # Updated mapping based on user's confirmed states
                if 'state' in server:
                    if server['state'] == 0:
                        status_text = "HIBERNATING"
                        status_color = "\033[91m" # Red
                    elif server['state'] == 1:
                        status_text = "PROCESSING"
                        status_color = "\033[93m" # Yellow
                    elif server['state'] == 5:
                        status_text = "OFFLINE"
                        status_color = "\033[91m" # Red
                    elif server['state'] == 3:
                        status_text = "STARTING"
                        status_color = "\033[93m" # Yellow
                    elif server['state'] == 4:
                        status_text = "RUNNING"
                        status_color = "\033[92m" # Green
                    elif server['state'] == 8:
                        status_text = "STOPPING"
                        status_color = "\033[94m" # Blue
                    # Add a default if state is not recognized
                    else:
                        status_text = f"UNKNOWN (State {server['state']})"
                        status_color = "\033[0m" # Reset color

                print(f"[{i+1}] {server.get('serverName', 'N/A')} (ID: {server.get('serverId', 'N/A')}) - Status: {status_color}{status_text.upper()}\033[0m")
            print("-----------------------------")

        # Display action menu
        print("\n--- Select Action ---")
        print("1. Refresh Server Status")
        print("2. Start a Server")
        print("3. Stop a Server")
        print("4. Hibernate a Server")
        print("5. Wake Up a Server (same as Start)")
        print("6. Exit")
        
        choice = input("Enter your choice (1-6): ").strip()

        if choice == '1':
            continue # Loop will re-fetch status
        elif choice in ['2', '3', '4', '5']:
            if not servers:
                print("No servers available to perform actions on. Please refresh status first.")
                continue

            try:
                server_index = int(input(f"Enter the number of the server (1-{len(servers)}) to perform action on: ")) - 1
                if 0 <= server_index < len(servers):
                    selected_server = servers[server_index]
                    server_id = selected_server['serverId'] # Use 'serverId' as per example response
                    
                    action_map = {
                        '2': 'start',
                        '3': 'kill',
                        '4': 'sleep',  # Corrected from 'hibernate' to 'sleep'
                        '5': 'wakeup'
                    }
                    action_type = action_map[choice]

                    result = perform_server_action(server_id, action_type)
                    print(f"\nAction Result: {result['status'].upper()} - {result['message']}")
                else:
                    print("Invalid server number. Please enter a number from the list.")
            except ValueError:
                print("Invalid input. Please enter a number for server selection.")
            except Exception as e:
                print(f"An unexpected error occurred during server action: {e}")
        elif choice == '6':
            print("Exiting Minefort Server Manager. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")
        
        input("\nPress Enter to continue...") # Pause for user to read output
