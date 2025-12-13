# utils/enhanced_auth_helper.py

import os
import webbrowser
from datetime import datetime, timedelta
from typing import Optional, Tuple
from fyers_apiv3 import fyersModel
import requests


class FyersAuthManager:
    """Enhanced Fyers authentication manager with token refresh support."""

    def __init__(self, client_id: str, secret_key: str, redirect_uri: str = "https://127.0.0.1/"):
        """
        Initialize the authentication manager.

        Args:
            client_id: Fyers API client ID
            secret_key: Fyers API secret key
            redirect_uri: OAuth redirect URI (default: https://127.0.0.1/)
        """
        self.client_id = client_id
        self.secret_key = secret_key
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None

    def generate_auth_code(self) -> str:
        """
        Generate authorization code via browser OAuth flow.

        Returns:
            Authorization code from OAuth flow
        """
        # Create auth session
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            grant_type="authorization_code"
        )

        # Generate auth URL
        auth_url = session.generate_authcode()
        print(f"Auth URL: {auth_url}\n")

        # Get authorization code from user
        print("After logging in, you'll be redirected to a URL like:")
        print("https://127.0.0.1/?s=ok&code=XXXXX&auth_code=YYYYY")
        print("\nPlease copy the complete redirected URL and paste it here:")

        redirect_url = input("Redirected URL: ").strip()

        # Extract auth code from URL
        if "auth_code=" in redirect_url:
            auth_code = redirect_url.split("auth_code=")[1].split("&")[0]
            return auth_code
        else:
            raise ValueError("Invalid redirect URL. Could not extract auth_code.")

    def generate_access_token(self, auth_code: str, pin: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate access token from authorization code.

        Args:
            auth_code: Authorization code from OAuth flow
            pin: Trading PIN (optional, for token refresh)

        Returns:
            Tuple of (access_token, refresh_token)
        """
        # Create session
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            grant_type="authorization_code"
        )

        # Set auth code
        session.set_token(auth_code)

        # Generate token
        response = session.generate_token()

        if response.get("code") == 200:
            self.access_token = response["access_token"]
            self.refresh_token = response.get("refresh_token", "")
            self.token_expiry = datetime.now() + timedelta(hours=24)

            print(f"\nAccess token generated successfully!")
            print(f"Token expires at: {self.token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")

            return self.access_token, self.refresh_token
        else:
            raise Exception(f"Token generation failed: {response}")

    def refresh_access_token(self, refresh_token: str, pin: str) -> str:
        """
        Refresh access token using refresh token and PIN.

        Note: Fyers API v3 requires manual re-authentication every 24 hours.
        This method is a placeholder for future API updates.

        Args:
            refresh_token: Refresh token from previous auth
            pin: Trading PIN

        Returns:
            New access token
        """
        print("Fyers API requires manual re-authentication every 24 hours.")
        print("Please run 'python main.py auth' to generate a new token.")
        raise NotImplementedError("Token refresh not supported by Fyers API v3")

    def is_token_valid(self) -> bool:
        """
        Check if current access token is still valid.

        Returns:
            True if token is valid, False otherwise
        """
        if not self.access_token or not self.token_expiry:
            return False

        # Check if token has expired (with 1-hour buffer)
        time_until_expiry = self.token_expiry - datetime.now()
        return time_until_expiry.total_seconds() > 3600

    def validate_token(self, access_token: str) -> bool:
        """
        Validate an access token by making a test API call.

        Args:
            access_token: Access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            fyers = fyersModel.FyersModel(
                client_id=self.client_id,
                is_async=False,
                token=access_token,
                log_path=""
            )

            # Test API call - get profile
            response = fyers.get_profile()

            if response.get("code") == 200:
                print(f"\nToken validated successfully!")
                print(f"User: {response.get('data', {}).get('name', 'Unknown')}")
                return True
            else:
                print(f"\nToken validation failed: {response}")
                return False
        except Exception as e:
            print(f"\nToken validation error: {str(e)}")
            return False

    def save_to_env(self, env_path: str = ".env") -> None:
        """
        Save authentication credentials to .env file.

        Args:
            env_path: Path to .env file
        """
        if not self.access_token:
            raise ValueError("No access token available to save")

        # Read existing .env
        env_vars = {}
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

        # Update tokens
        env_vars['FYERS_ACCESS_TOKEN'] = self.access_token
        if self.refresh_token:
            env_vars['FYERS_REFRESH_TOKEN'] = self.refresh_token
        env_vars['FYERS_TOKEN_EXPIRY'] = self.token_expiry.isoformat()

        # Write back to .env
        with open(env_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        print(f"\nCredentials saved to {env_path}")

    def load_from_env(self, env_path: str = ".env") -> bool:
        """
        Load authentication credentials from .env file.

        Args:
            env_path: Path to .env file

        Returns:
            True if credentials loaded successfully, False otherwise
        """
        if not os.path.exists(env_path):
            return False

        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('FYERS_ACCESS_TOKEN='):
                    self.access_token = line.split('=', 1)[1].strip()
                elif line.startswith('FYERS_REFRESH_TOKEN='):
                    self.refresh_token = line.split('=', 1)[1].strip()
                elif line.startswith('FYERS_TOKEN_EXPIRY='):
                    expiry_str = line.split('=', 1)[1].strip()
                    try:
                        self.token_expiry = datetime.fromisoformat(expiry_str)
                    except ValueError:
                        pass

        return bool(self.access_token)


# Convenience functions

def setup_auth(client_id: str, secret_key: str, redirect_uri: str = "https://127.0.0.1/",
               pin: Optional[str] = None) -> Tuple[str, str]:
    """
    Complete authentication setup flow.

    Args:
        client_id: Fyers API client ID
        secret_key: Fyers API secret key
        redirect_uri: OAuth redirect URI (default: https://127.0.0.1/)
        pin: Trading PIN (optional)

    Returns:
        Tuple of (access_token, refresh_token)
    """
    auth_manager = FyersAuthManager(client_id, secret_key, redirect_uri)  # ← Pass redirect_uri here

    # Step 1: Generate auth code
    auth_code = auth_manager.generate_auth_code()

    # Step 2: Generate access token
    access_token, refresh_token = auth_manager.generate_access_token(auth_code, pin)

    # Step 3: Save to .env
    auth_manager.save_to_env()

    return access_token, refresh_token


def test_authentication(client_id: str, access_token: str) -> bool:
    """
    Test authentication by validating access token.

    Args:
        client_id: Fyers API client ID
        access_token: Access token to test

    Returns:
        True if authentication successful, False otherwise
    """
    auth_manager = FyersAuthManager(client_id, "", "")
    return auth_manager.validate_token(access_token)


def update_pin(pin: str, env_path: str = ".env") -> None:
    """
    Update trading PIN in .env file.

    Args:
        pin: New trading PIN
        env_path: Path to .env file
    """
    # Read existing .env
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

    # Update PIN
    env_vars['FYERS_PIN'] = pin

    # Write back to .env
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(f"\n✅ Trading PIN updated in {env_path}")