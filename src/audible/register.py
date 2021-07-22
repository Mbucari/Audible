from datetime import datetime, timedelta
from typing import Any, Dict

import httpx

from .login import build_client_id


def _build_registration_body(domain: str, serial: str) -> Dict:
    """Builds the registration body except the auth_data"""
    return {
        "requested_token_type":
            ["bearer", "mac_dms", "website_cookies",
             "store_authentication_cookie"],
        "cookies": {
            "website_cookies": [],
            "domain": f".amazon.{domain}"},
        "registration_data": {
            "domain": "Device",
            "app_version": "3.26.1",
            "device_serial": serial,
            "device_type": "A2CZJZGLK2JJVM",
            "device_name": (
                "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_"
                "STRATEGY_1ST%Audible for iPhone"),
            "os_version": "13.5.1",
            "device_model": "iPhone",
            "app_name": "Audible"},
        "requested_extensions": ["device_info", "customer_info"]
    }


def _register(body: Dict, domain: str) -> Dict[str, Any]:
    resp = httpx.post(f"https://api.amazon.{domain}/auth/register", json=body)

    resp_json = resp.json()
    if resp.status_code != 200:
        raise Exception(resp_json)

    success_response = resp_json["response"]["success"]

    tokens = success_response["tokens"]
    adp_token = tokens["mac_dms"]["adp_token"]
    device_private_key = tokens["mac_dms"]["device_private_key"]
    store_authentication_cookie = tokens["store_authentication_cookie"]
    access_token = tokens["bearer"]["access_token"]
    refresh_token = tokens["bearer"]["refresh_token"]
    expires_s = int(tokens["bearer"]["expires_in"])
    expires = (datetime.utcnow() + timedelta(seconds=expires_s)).timestamp()

    extensions = success_response["extensions"]
    device_info = extensions["device_info"]
    customer_info = extensions["customer_info"]

    website_cookies = dict()
    for cookie in tokens["website_cookies"]:
        website_cookies[cookie["Name"]] = cookie["Value"].replace(r'"', r'')

    return {
        "adp_token": adp_token,
        "device_private_key": device_private_key,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires": expires,
        "website_cookies": website_cookies,
        "store_authentication_cookie": store_authentication_cookie,
        "device_info": device_info,
        "customer_info": customer_info
    }


def register(access_token: str, domain: str, serial: str) -> Dict[str, Any]:
    """Register a new Audible device with access token. 

    Args:
        access_token: An access token fetches from :func:`audible.auth.login`.
        domain: The top level domain of the requested Amazon server (e.g. com).
    
    Returns:
        Additional authentication data needed for access Audible API.
    """
    body = _build_registration_body(domain=domain, serial=serial)
    body["auth_data"] = {"access_token": access_token}
    return _register(body=body, domain=domain)


def register_auth_code(authorization_code: str,
                       code_verifier: str,
                       domain: str,
                       serial: str) -> Dict[str, Any]:
    """Register a new Audible device with authorization code. 

    Args:
        authorization_code: Login in `auth_code` mode to get the code.
        code_verifier: The code verifier used at login to create the code challenge.
        domain: The top level domain of the requested Amazon server (e.g. com).
        serial: The device serial used at login.
    
    Returns:
        Additional authentication data needed for access Audible API.
    """
    body = _build_registration_body(domain=domain, serial=serial)
    body["auth_data"] = {
        "client_id" : build_client_id(serial),
        "authorization_code" : authorization_code,
        "code_verifier" : code_verifier,
        "code_algorithm" : "SHA-256",
        "client_domain" : "DeviceLegacy"
    }
    return _register(body=body, domain=domain)


def deregister(access_token: str, domain: str,
               deregister_all: bool = False) -> Dict[str, Any]:
    """Deregisters a previous registered Audible device.
    
    Note:
        Except of the ``access_token``, all authentication data will loose 
        validation immediately.

    Args:
        access_token: The access token from the previous registered device 
            which you want to deregister.
        domain: The top level domain of the requested Amazon server (e.g. com).
        deregister_all: If ``True``, deregister all Audible devices on Amazon.

    Returns:
        The response for the deregister request. Contains errors, if some occurs.
    """
    body = {"deregister_all_existing_accounts": deregister_all}
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = httpx.post(
        f"https://api.amazon.{domain}/auth/deregister",
        json=body,
        headers=headers
    )

    resp_json = resp.json()
    if not resp.status_code == 200:
        raise Exception(resp_json)

    return resp_json
