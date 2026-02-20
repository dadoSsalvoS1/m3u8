import sys
import os
import unittest

# Add src to path so we can import the package
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ipfs_iptv.config import Config
from ipfs_iptv.ipfs_client import IPFSClient
from ipfs_iptv.media_scanner import MediaScanner
from ipfs_iptv.playlist_generator import PlaylistGenerator

class TestBasic(unittest.TestCase):
    def test_config_defaults(self):
        c = Config()
        self.assertEqual(c.ipfs_api_url, "http://127.0.0.1:5001/api/v0")
        self.assertTrue(c.ipfs_gateway_url.endswith("/"))

    def test_scanner_init(self):
        c = Config()
        s = MediaScanner(c)
        self.assertIsInstance(s, MediaScanner)

    def test_generator_init(self):
        c = Config()
        g = PlaylistGenerator(c)
        self.assertIsInstance(g, PlaylistGenerator)

if __name__ == '__main__':
    unittest.main()
