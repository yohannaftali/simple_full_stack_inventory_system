import json
import requests
import urllib3

import flet as ft

from repository.server_url import ServerURL
from repository.http_cookies import HttpCookies


class HttpClient:
    """HTTP client utility for making API requests"""

    def __init__(self, page: ft.Page, verify: bool = False):
        """HTTP client utility for making API requests.

        Args:
            page: Flet page instance (used for ServerURL and cookies).
            verify: Whether to verify TLS certificates. Defaults to False for local dev.
                For production with valid certs, pass `verify=True`.
                If `verify` is a string path to a CA bundle, that path will be
                used by requests (requests accepts bool or path string).
        """
        base_url = ServerURL(page).get()
        cookies = HttpCookies(page).get()
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if cookies is not None:
            self.session.cookies.clear()
            self.session.cookies.update(cookies)

        self.verify = verify
        if self.verify is False:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def get_cookies(self) -> dict | None:
        print(f"Get cookies: {self.session.cookies}")
        if self.session.cookies is None:
            return None
        # Handle duplicate cookie names by using the latest one
        cookies_dict = {}
        for cookie in self.session.cookies:
            # Always overwrite with the latest cookie value
            cookies_dict[cookie.name] = cookie.value
        return cookies_dict

    def get(self, endpoint: str, params: dict = None):
        """Make a GET request

        `timeout` (below, and on `post()`) is in SECONDS, per `requests`'
        own API - the previous value of `300000` was a units bug (meant as
        milliseconds, ~83 hours as seconds), making a request against an
        unreachable server effectively hang forever. Combined with
        `main.py`'s boot sequence calling this synchronously (blocking the
        whole single-threaded asyncio event loop, no `asyncio.to_thread`
        wrap - see that file's own fix), this was the root cause of a
        connecting client (e.g. the dev-mode QR-scan companion app)
        appearing permanently stuck on "Connecting..." whenever the
        persisted `server_url` pointed at a currently-unreachable backend.
        """
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            print(f"GET Request: {url}")
            print(f"GET Params: {params}")
            response = self.session.get(
                url, params=params, timeout=30, allow_redirects=False, verify=self.verify)
            print(f"GET Status Code: {response.status_code}")

            # Check for redirects (usually means authentication failed)
            if response.status_code in [301, 302, 303, 307, 308]:
                redirect_location = response.headers.get('Location', 'Unknown')
                error = {"error": "Redirect detected - Authentication required or session expired",
                         "redirect_to": redirect_location}
                print(f"GET Redirect: {error}")
                return error

            # Return status code and response for caller to handle
            response.raise_for_status()

            try:
                result = response.json()
                print(f"GET Response json: {result}")
                return result
            except json.JSONDecodeError:
                # Not valid JSON, handle as text
                text = response.text.strip()
                print(f"POST Response (Text): '{text}'")
                print(f"POST Response Length: {len(text)}")

                if text.lower() == 'true' or text == '1':
                    return True
                elif text.lower() == 'false' or text == '0':
                    return False
                elif text == '':
                    # Empty response - return status code for caller to interpret
                    return {"status_code": response.status_code}
                else:
                    return {"response": text}
        except requests.exceptions.Timeout:
            error = {"error": "Request timeout"}
            print(f"GET Error: {error}")
            return error
        except requests.exceptions.ConnectionError:
            error = {"error": "Connection error"}
            print(f"GET Error: {error}")
            return error
        except requests.exceptions.HTTPError:
            # Return error with status code for caller to handle
            error = {"error": f"HTTP {response.status_code}",
                     "status_code": response.status_code}
            print(f"GET Error: {error}")
            return error
        except requests.exceptions.RequestException as e:
            error = {"error": str(e)}
            print(f"GET Error: {error}")
            return error
        except json.JSONDecodeError as e:
            result = {"response": response.text}
            print(f"GET Response (JSON Decode Error): {result}")
            return result
        except Exception as e:
            error = {"error": f"Unexpected error: {str(e)}"}
            print(f"GET Error: {error}")
            return error

    def post(self, endpoint: str, data: dict = None):
        """Make a POST request"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            print(f"POST Request: {url}")
            print(f"POST Data: {data}")
            response = self.session.post(
                url, data=data, timeout=30, allow_redirects=False, verify=self.verify)
            print(f"POST Status Code: {response.status_code}")

            # Check for redirects (usually means authentication failed)
            if response.status_code in [301, 302, 303, 307, 308]:
                redirect_location = response.headers.get('Location', 'Unknown')
                error = {"error": "Redirect detected - Authentication required or session expired",
                         "redirect_to": redirect_location, "status_code": response.status_code}
                print(f"POST Redirect: {error}")
                return error

            # Return status code and response for caller to handle
            response.raise_for_status()

            try:
                result = response.json()
                print(f"POST Response (JSON): {result}")
                return result
            except json.JSONDecodeError:
                # Not valid JSON, handle as text
                text = response.text.strip()
                print(f"POST Response (Text): '{text}'")
                print(f"POST Response Length: {len(text)}")

                if text.lower() == 'true' or text == '1':
                    return True
                elif text.lower() == 'false' or text == '0':
                    return False
                elif text == '':
                    # Empty response - return status code for caller to interpret
                    return {"status_code": response.status_code}
                else:
                    return {"response": text}
        except requests.exceptions.Timeout:
            error = {"error": "Request timeout"}
            print(f"POST Error: {error}")
            return error
        except requests.exceptions.ConnectionError:
            error = {"error": "Connection error"}
            print(f"POST Error: {error}")
            return error
        except requests.exceptions.HTTPError:
            # Return error with status code for caller to handle
            error = {"error": f"HTTP {response.status_code}",
                     "status_code": response.status_code}
            print(f"POST Error: {error}")
            return error
        except requests.exceptions.RequestException as e:
            error = {"error": str(e)}
            print(f"POST Error: {error}")
            return error
        except json.JSONDecodeError:
            result = {"response": response.text}
            print(f"POST Response (JSON Decode Error): {result}")
            return result
        except Exception as e:
            error = {"error": f"Unexpected error: {str(e)}"}
            print(f"POST Error: {error}")
            return error
