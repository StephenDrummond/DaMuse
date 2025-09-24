# 🎵 Collective Music Bot

A **Discord music bot** that automatically curates, plays, and shuffles tracks based on a **shared genre profile** derived from the combined preferences of everyone in a voice channel.

By tracking recent play requests from channel participants, the bot builds a **dynamic, community-driven playlist** that adapts as users join or leave, creating an evolving listening experience tailored to the current audience.

---

## 🔹 Key Features
- **Automatic Playlist Generation** — Scans recent play requests from all users in the voice channel to build a collaborative genre profile.
- **Community-Driven Music** — Plays songs that match the tastes of the current listeners.
- **Dynamic Adaptation** — Updates playlists in real time as users join or leave the voice channel.
- **Shuffle & Radio Mode** — Creates a seamless, ongoing playlist for a shared listening experience.
- **Multi-Source Support** — Works with Spotify, YouTube, and other streaming sources for maximum flexibility.

---

## 💡 How It Works
1. **Track Play Requests** — Monitors song requests submitted by members of a voice channel.  
2. **Analyze Genres** — Extracts genre data from those requests to create a profile of collective tastes.  
3. **Generate Radio Playlist** — Compiles a playlist matching the genre profile.  
4. **Play & Shuffle** — Streams music directly into the voice channel with shuffle and continuous playback.

---

## ⚙️ Use Case
Perfect for:
- Discord communities who want a shared listening experience.
- Gaming groups looking for dynamic background music.
- Study sessions with collaborative playlists.
- Social channels where music is part of the shared experience.

---

## 📂 Project Structure
my_music_bot/

├── muse.py                  # Main bot entry point

├── cogs/                   # Command modules

├── utils/                  # Utility functions

├── .env                    # Secret keys

├── requirements.txt        # Dependencies

├── README.md               # This file

___
