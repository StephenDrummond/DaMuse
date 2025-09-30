/**
 * TEMPORARY MODEL INDEX - IN-MEMORY DATABASE
 * 
 * ⚠️  WARNING: THIS IS TEMPORARY CODE FOR TESTING PURPOSES ONLY ⚠️
 * 
 * This file provides temporary model exports that use in-memory storage
 * instead of MongoDB. All data will be lost when the bot restarts.
 * 
 * TO CLEAN UP:
 * 1. Delete this file: models/tempIndex.js
 * 2. Restore original model files from git
 * 3. Update imports in other files to use original models
 */

// Export temporary models
const TempSong = require('./tempSong');
const TempUserPreference = require('./tempUserPreference');
const TempMusicInteraction = require('./tempMusicInteraction');

module.exports = {
    Song: TempSong,
    UserPreference: TempUserPreference,
    MusicInteraction: TempMusicInteraction
};
