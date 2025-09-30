# DaMuse.js MongoDB Setup & Music Recommendation System

## 🎵 Overview

DaMuse.js now includes a comprehensive MongoDB-based music recommendation system that learns from user preferences and provides intelligent autoplay functionality.

## 🚀 Features

### Core Features
- **MongoDB Integration**: Full database support for songs, user preferences, and interactions
- **Music Recommendation Engine**: AI-powered song suggestions based on listening history
- **Autoplay System**: Automatic music queuing based on user preferences
- **Context Menu Commands**: Like/Dislike songs with right-click context menus
- **User Preference Learning**: Tracks and learns from user music taste
- **Analytics**: Comprehensive music listening analytics

### New Commands
- `/autoplay` - Enable/disable intelligent autoplay
- `/recommendations` - Get personalized music recommendations
- **Context Menus**: Right-click on music messages to like/dislike songs

## 📋 Prerequisites

1. **MongoDB Database**
   - Local MongoDB installation OR
   - MongoDB Atlas cloud database

2. **Environment Variables**
   ```env
   DISCORD_TOKEN=your_discord_bot_token
   CLIENT_ID=your_discord_application_id
   GUILD_ID=your_discord_guild_id
   MONGO_URI=mongodb://localhost:27017/damuse
   ```

## 🛠️ Installation

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Set up MongoDB**
   - **Local**: Install MongoDB locally and start the service
   - **Atlas**: Create a MongoDB Atlas cluster and get connection string

3. **Configure Environment**
   - Copy `.env.example` to `.env`
   - Fill in your Discord and MongoDB credentials

4. **Deploy Commands**
   ```bash
   npm run deploy
   ```

5. **Start the Bot**
   ```bash
   npm start
   ```

## 🗄️ Database Schema

### Songs Collection
```javascript
{
  title: String,
  artist: String,
  url: String,
  thumbnail: String,
  duration: Number,
  genre: String,
  mood: String,
  energy: Number (1-10),
  playCount: Number,
  likeCount: Number,
  dislikeCount: Number,
  skipCount: Number,
  recommendationScore: Number (0-1)
}
```

### User Preferences Collection
```javascript
{
  userId: String,
  guildId: String,
  genrePreferences: Map<String, Number>,
  artistPreferences: Map<String, Number>,
  moodPreferences: Map<String, Number>,
  preferredEnergyRange: { min: Number, max: Number },
  autoplayEnabled: Boolean,
  totalSongsPlayed: Number,
  totalListeningTime: Number
}
```

### Music Interactions Collection
```javascript
{
  userId: String,
  guildId: String,
  songId: ObjectId,
  interactionType: String, // 'play', 'like', 'dislike', 'skip', 'complete'
  playedAt: Date,
  duration: Number,
  wasAutoplay: Boolean,
  wasRecommended: Boolean
}
```

## 🎯 How It Works

### 1. Song Learning
- When users play songs, they're automatically saved to the database
- Song metadata (title, artist, genre, etc.) is extracted and stored
- Play counts and interaction data are tracked

### 2. User Preference Learning
- System tracks user interactions (likes, dislikes, skips)
- Builds preference profiles for genres, artists, and moods
- Learns energy level preferences and listening patterns

### 3. Recommendation Algorithm
- **Genre Weight**: 30% - Based on user's preferred genres
- **Artist Weight**: 25% - Based on liked artists
- **Mood Weight**: 20% - Based on preferred moods
- **Energy Weight**: 15% - Based on energy level preferences
- **Popularity Weight**: 10% - Based on overall song popularity

### 4. Autoplay System
- Automatically adds recommended songs to queue
- Considers multiple users' preferences in the same guild
- Falls back to trending songs when preferences are insufficient
- Respects cooldown periods to avoid spam

## 🎮 Usage

### Basic Commands
```bash
/play <song>          # Play a song (automatically saved to database)
/autoplay enable      # Enable intelligent autoplay
/autoplay disable     # Disable autoplay
/recommendations      # Get personalized recommendations
/queue                # View current queue
/skip                 # Skip current song
/stop                 # Stop playback
```

### Context Menu Actions
- Right-click on music messages
- Select "Like Song" or "Dislike Song"
- System learns from your preferences

### Autoplay Features
- **Smart Recommendations**: Learns from your music taste
- **Multi-User Support**: Considers all users' preferences in the guild
- **Trending Fallback**: Uses popular songs when preferences are limited
- **Cooldown Management**: Prevents excessive autoplay

## 📊 Analytics & Insights

The system tracks comprehensive analytics:

- **Song Statistics**: Play counts, likes, dislikes, skips
- **User Preferences**: Favorite genres, artists, moods
- **Listening Patterns**: Total time, songs played, interaction rates
- **Recommendation Performance**: Success rates of autoplay suggestions

## 🔧 Configuration

### Recommendation Sensitivity
Users can adjust how sensitive the recommendation system is:
- **High Sensitivity**: More personalized, fewer popular songs
- **Low Sensitivity**: More popular songs, less personalization

### Autoplay Settings
- **Enable/Disable**: Per-user autoplay preferences
- **Cooldown Periods**: Minimum time between autoplay additions
- **Queue Limits**: Maximum autoplay songs in queue

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check MongoDB is running
   - Verify MONGO_URI in .env file
   - Ensure network connectivity

2. **No Recommendations Available**
   - Play more songs to build preference data
   - Use like/dislike context menus
   - Check if autoplay is enabled

3. **Context Menus Not Working**
   - Redeploy commands: `npm run deploy`
   - Check bot permissions
   - Ensure context menus are enabled

### Performance Optimization

- **Indexing**: Database indexes are automatically created for optimal performance
- **Caching**: Recommendation results are cached to reduce database load
- **Cleanup**: Automatic cleanup of old interaction data

## 🔮 Future Enhancements

- **Spotify Integration**: Enhanced metadata from Spotify API
- **Genre Detection**: Automatic genre classification using AI
- **Mood Analysis**: Advanced mood detection from audio features
- **Collaborative Filtering**: Recommendations based on similar users
- **Playlist Generation**: Automatic playlist creation based on preferences

## 📝 API Reference

### Recommendation Engine
```javascript
const recommendationEngine = require('./utils/recommendationEngine');

// Get recommendations for a user
const recommendations = await recommendationEngine.getRecommendations(userId, guildId, limit);

// Get similar songs
const similar = await recommendationEngine.getSimilarSongs(songId, limit);

// Get trending songs
const trending = await recommendationEngine.getTrendingSongs(guildId, limit, timeRange);
```

### Autoplay Manager
```javascript
const autoplayManager = require('./utils/autoplayManager');

// Enable autoplay
autoplayManager.enableAutoplay(guildId, userId);

// Get next autoplay song
const nextSong = await autoplayManager.getNextAutoplaySong(guildId, currentSongId);

// Get autoplay statistics
const stats = await autoplayManager.getAutoplayStats(guildId);
```

## 🎉 Conclusion

DaMuse.js now provides a sophisticated music recommendation system that learns from user behavior and provides intelligent autoplay functionality. The system is designed to improve over time as it learns more about user preferences and music patterns.

Enjoy your personalized music experience! 🎵
