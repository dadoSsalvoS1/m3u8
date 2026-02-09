import os
import requests
import json
import logging
from typing import Optional, Tuple
from .config import Config

logger = logging.getLogger(__name__)

class IPFSConnectionError(Exception):
    """Raised when unable to connect to IPFS API."""
    pass

class IPFSUploadError(Exception):
    """Raised when file upload fails."""
    pass

class IPFSClient:
    def __init__(self, config: Config):
        self.config = config
        self.api_url = config.ipfs_api_url.rstrip('/')

    def check_connection(self) -> bool:
        """Checks if the IPFS daemon is reachable."""
        try:
            # Check version or id to verify connection
            response = requests.post(f"{self.api_url}/id", timeout=5)
            response.raise_for_status()
            logger.info(f"Connected to IPFS node: {response.json().get('ID')}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to IPFS at {self.api_url}. Is IPFS Desktop running? Error: {e}")
            return False

    def add_file(self, filepath: str) -> str:
        """
        Uploads a file to IPFS and returns its CID.
        Uses multipart/form-data upload via IPFS API /add endpoint.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        filename = os.path.basename(filepath)

        try:
            with open(filepath, 'rb') as f:
                # Basic upload without progress bar inside the request to ensure stability
                files = {'file': (filename, f, 'application/octet-stream')}
                params = {'pin': 'true', 'wrap-with-directory': 'false'}

                response = requests.post(
                    f"{self.api_url}/add",
                    files=files,
                    params=params,
                    timeout=300 # 5 minutes timeout for large files
                )

            response.raise_for_status()

            # The response might be multiple JSON objects if the directory wrapper was used,
            # but we disabled it.
            try:
                result = response.json()
            except json.JSONDecodeError:
                # Sometimes IPFS returns multiple JSONs concatenated (NDJSON)
                # We take the last one which is usually the root or the file
                lines = response.text.strip().split('\n')
                result = json.loads(lines[-1])

            cid = result.get('Hash')
            if not cid:
                raise IPFSUploadError(f"No Hash returned in response: {result}")

            logger.info(f"Uploaded {filename} -> CID: {cid}")
            return cid

        except requests.exceptions.RequestException as e:
            raise IPFSUploadError(f"Network error during upload of {filepath}: {e}")
        except Exception as e:
            raise IPFSUploadError(f"Unexpected error during upload of {filepath}: {e}")

    def pin_cid(self, cid: str) -> bool:
        """
        Pins a CID to the local node.
        """
        try:
            response = requests.post(f"{self.api_url}/pin/add", params={'arg': cid}, timeout=60)
            response.raise_for_status()
            logger.info(f"Pinned CID: {cid}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to pin CID {cid}: {e}")
            return False

    def get_cid_base32(self, cid: str) -> str:
        """
        Converts a CID (usually v0, Qm...) to CIDv1 base32 (bafy...).
        Useful for subdomain gateways like dweb.link.
        """
        try:
            # IPFS API endpoint: /api/v0/cid/base32?arg=<cid>
            response = requests.post(f"{self.api_url}/cid/base32", params={'arg': cid}, timeout=10)
            response.raise_for_status()

            # Response is typically JSON: {"CidStr": "bafy..."}
            # Or plaintext depending on version, but usually JSON for API.
            # Let's handle both.
            try:
                data = response.json()
                return data.get('CidStr', cid)
            except json.JSONDecodeError:
                return response.text.strip()

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to convert CID {cid} to base32: {e}")
            return cid
