# tests/test_spotify.py
import unittest

from utils.spotify import get_spotify_info


class SpotifyUtilsTest(unittest.TestCase):
    def test_get_spotify_track_info(self):
        link = "https://open.spotify.com/track/1xzBco0xcoJEDXktl7Jxrr?si=2071ffba782a463e"
        info = get_spotify_info(link)

        # Assertions to confirm function returns expected structure
        self.assertIsInstance(info, dict)
        self.assertIn("name", info)
        self.assertIn("artists", info)
        self.assertIn("album", info)
        self.assertIn("preview_url", info)

        # Optionally check exact values if known
        self.assertEqual(info["name"], "Mo Bamba")
        self.assertEqual(info["artists"], ["Sheck Wes"])
        self.assertEqual(info["album"], "MUDBOY")


if __name__ == "__main__":
    unittest.main()
