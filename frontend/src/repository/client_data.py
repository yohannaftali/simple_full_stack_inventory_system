"""
Client data utility for managing home data across the application
"""
import flet as ft

from utils.http_client import HttpClient


class ClientData:
    """Client data manager for storing and retrieving home data"""

    def __init__(self, page: ft.Page):
        """
        Initialize client data manager

        Args:
            page: The Flet page
        """
        self.page = page

    def refresh(self):
        """
        Load home data from server and store in client storage

        Returns:
            dict: Home data dictionary or None if failed
        """
        client = HttpClient(self.page)
        response = client.get("C_home/home")

        # Check if token expired (redirect detected)
        if isinstance(response, dict) and "error" in response:
            if "redirect" in response["error"].lower() or "authentication" in response["error"].lower():
                print("Token expired or not authenticated")
                return None

        # Store home data
        if isinstance(response, dict) and "modules" in response:
            self.set(response)
            self.page.title = response.get("title", "SFSIS")
            self.page.footer = response.get("footer", "")
            return response

        return None

    def set(self, client_data: dict):
        """
        Store client data in client storage

        Args:
            client_data: Dictionary containing client data
        """

        self.page.data["client_data"] = client_data

    def get(self, if_none=None):
        """
        Get client data from client storage

        Returns:
            dict: Client data dictionary or None if not found
        """
        return self.page.data.get("client_data", if_none)

    def get_modules(self):
        """
        Get modules list from client data

        Returns:
            list: List of modules or empty list
        """
        client_data = self.get()
        if client_data:
            return client_data.get("modules", [])
        return []

    def get_module_by_name(self, module_name):
        """
        Get specific module data from client data

        Args:
            module_name: Name of the module to retrieve
        """
        client_data = self.get()
        if not client_data:
            return None

        modules = client_data.get("modules")
        if not isinstance(modules, list):
            return None

        # Early return on first match - already O(n) optimal
        for m in modules:
            if m.get("name") == module_name:
                return m

        return None

    def find_modules(self, query, case_insensitive=True, partial=True):
        """Search modules by name or label.

        Args:
            query (str): search string.
            case_insensitive (bool): perform case-insensitive matching.
            partial (bool): allow substring match; if False use exact match.

        Returns:
            list[dict]: list of matching module dicts.
        """
        query = str(query or "").strip()
        if not query:
            return []
        client_data = self.get()
        if not client_data:
            return []
        modules = client_data.get("modules", [])
        if not isinstance(modules, list):
            return []
        if case_insensitive:
            q_cmp = query.lower()

            def match(val):
                if not isinstance(val, str):
                    return False
                v = val.lower()
                return v == q_cmp if not partial else q_cmp in v
        else:
            def match(val):
                if not isinstance(val, str):
                    return False
                return val == query if not partial else query in val
        results = []
        for m in modules:
            name_val = m.get("name")
            label_val = m.get("label")
            if match(name_val) or match(label_val):
                results.append(m)

        return results

    def get_username(self):
        """
        Get username from client data

        Returns:
            str: Username or "User" as default
        """
        client_data = self.get()
        if client_data:
            return client_data.get("username", "User")

        return "User"

    def get_title(self):
        """
        Get title from client data

        Returns:
            str: Title or "SFSIS" as default
        """
        client_data = self.get()
        if client_data:
            return client_data.get("title", "SFSIS")

        return "SFSIS"

    def get_footer(self):
        """
        Get footer text from client data

        Returns:
            str: Footer text or empty string
        """
        client_data = self.get()
        if client_data:
            return client_data.get("footer", "")

        return ""

    def clear(self):
        """Clear client data from client storage"""
        if not hasattr(self.page, "data") or self.page.data is None:
            self.page.data = {}

        self.page.data.pop("client_data", None)

    def is_active(self):
        """Return true if session still active"""
        response = self.refresh()
        if response is None:
            return False
        return True

    def has_permission(self, try_module):
        """Check if user has permission for a specific module"""
        modules = self.get_modules()
        if modules is None:
            print("No modules found in client data")
            return False

        module = self.get_module_by_name(try_module)
        if module is None:
            return False

        try:
            client = HttpClient(self.page)
            response = client.get(f"C_{try_module}")
            
            # Handle error responses
            if isinstance(response, dict) and "error" in response:
                print(f"Permission check failed: {response.get('error')}")
                return False
            
            if isinstance(response, dict) and "secure" in response:
                secure = response.get("secure", {})
                access = secure.get("access", False)
                print(access)
                return access
            else:
                print("Permission not found")
                return False
        except Exception as e:
            print(f"Error checking session: {e}")
            return False
