import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from utils.profiler import Profiler


class TestProfiler(unittest.IsolatedAsyncioTestCase):

    @patch("utils.profiler.get_spotify_info", new_callable=AsyncMock)
    @patch("utils.profiler.Database")
    async def test_log_user_play_event(self, mock_database_class, mock_get_spotify_info):
        # Arrange

        # Mock Spotify info
        mock_get_spotify_info.return_value = {
            "name": "Test Song",
            "artists": ["Test Artist"],
            "genres": ["Rock", "Pop"]
        }

        # Mock database methods
        mock_db_instance = MagicMock()
        mock_db_instance.fetch_val = AsyncMock(side_effect=[1, 2, 3, 4])  # song_id, artist_id, genre_id...
        mock_db_instance.execute = AsyncMock()
        mock_database_class.return_value = mock_db_instance

        # Create Profiler
        profiler = Profiler()

        # Mock Discord member
        member = MagicMock(spec=discord.Member)
        member.id = 12345

        # Act
        await profiler.log_user_play_event(member, "Test Song")

        # Assert: Spotify info called
        mock_get_spotify_info.assert_called_once_with("Test Song")

        # Assert: Database fetch_val calls (song, artist, genres)
        expected_fetch_calls = [
            unittest.mock.call("SELECT id FROM songs WHERE title = $1", "Test Song"),
            unittest.mock.call("SELECT id FROM artists WHERE name = $1", "Test Artist"),
            unittest.mock.call("SELECT id FROM genres WHERE name = $1", "Rock"),
            unittest.mock.call("SELECT id FROM genres WHERE name = $1", "Pop"),
        ]
        mock_db_instance.fetch_val.assert_has_calls(expected_fetch_calls, any_order=False)

        # Assert: upsert_like inserts
        self.assertEqual(mock_db_instance.execute.call_count, 4)

        insert_queries = [call.args[0] for call in mock_db_instance.execute.call_args_list]
        self.assertTrue(all("INSERT INTO" in q for q in insert_queries))
