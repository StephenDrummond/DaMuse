# DaMuse Discord Music Bot

A powerful Discord music bot with advanced features including collaborative mixing, personalized recommendations, and autoplay functionality.

## Features

- 🎵 **Music Playback**: Play music from YouTube with high-quality audio
- 🤖 **Autoplay**: Intelligent music recommendations based on user preferences
- 👥 **Collaborative Mixing**: Create mixes based on all users in voice channel
- 📊 **Analytics**: Music statistics and user preference tracking
- 🎯 **Personalized Recommendations**: AI-powered song suggestions
- ⚡ **Real-time Interaction**: Like/dislike songs to improve recommendations

## Quick Start

### 1. Prerequisites
- Node.js 18.0.0 or higher
- Discord Bot Token
- Discord Application ID

### 2. Installation
```bash
# Clone the repository
git clone <repository-url>
cd DaMusejs

# Install dependencies
npm install
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
CLIENT_ID=your_discord_application_id_here
GUILD_ID=your_test_server_id_here

# Optional: MongoDB Configuration (currently using temporary in-memory database)
MONGO_URI=mongodb://localhost:27017/damuse

# Optional: Spotify API (for future Spotify integration)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

### 4. Deploy Commands
```bash
# Deploy slash commands to Discord (first time only)
npm run deploy
```

### 5. Start the Bot
```bash
# Development mode (with auto-restart)
npm run dev

# Production mode
npm start
```

## Commands

| Command | Description |
|---------|-------------|
| `/play <song>` | Play a song or add to queue |
| `/queue` | View current music queue |
| `/skip` | Skip current song |
| `/stop` | Stop music and clear queue |
| `/like` | Like the current song |
| `/dislike` | Dislike the current song |
| `/autoplay <enable/disable>` | Enable/disable autoplay |
| `/mix [count] [mode]` | Create collaborative mix |
| `/mixstats` | View music statistics |
| `/recommendations [count]` | Get personalized recommendations |

## Database

Currently using a **temporary in-memory database** for testing:
- ✅ No MongoDB setup required
- ⚠️ All data is lost when bot restarts
- 🔄 Perfect for development and testing

To use MongoDB in production, update the database connection in `DaMuse.js`.

## Development

### Project Structure
```
DaMusejs/
├── cogs/                 # Slash commands
├── models/              # Database models
├── music_state/         # Queue and inactivity management
├── utils/               # Utility functions
├── contextMenus/        # Context menu interactions
├── config/              # Configuration files
└── DaMuse.js           # Main bot file
```

### Scripts
- `npm start` - Start the bot
- `npm run dev` - Start with nodemon (auto-restart)
- `npm run deploy` - Deploy slash commands

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions, please open an issue on GitHub.