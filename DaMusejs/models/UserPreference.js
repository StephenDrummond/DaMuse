const mongoose = require('mongoose');

// Define the schema for user music preferences
const userPreferenceSchema = new mongoose.Schema({
    userId: {
        type: String,
        required: true,
        index: true
    },
    guildId: {
        type: String,
        required: true,
        index: true
    },
    
    // Genre preferences (weighted)
    genrePreferences: {
        type: Map,
        of: Number, // Weight from 0-1
        default: new Map()
    },
    
    // Artist preferences
    artistPreferences: {
        type: Map,
        of: Number, // Weight from 0-1
        default: new Map()
    },
    
    // Mood preferences
    moodPreferences: {
        type: Map,
        of: Number, // Weight from 0-1
        default: new Map()
    },
    
    // Energy level preferences
    preferredEnergyRange: {
        min: {
            type: Number,
            min: 1,
            max: 10,
            default: 1
        },
        max: {
            type: Number,
            min: 1,
            max: 10,
            default: 10
        }
    },
    
    // Listening history
    totalSongsPlayed: {
        type: Number,
        default: 0,
        min: 0
    },
    totalListeningTime: {
        type: Number, // In minutes
        default: 0,
        min: 0
    },
    
    // Interaction statistics
    totalLikes: {
        type: Number,
        default: 0,
        min: 0
    },
    totalDislikes: {
        type: Number,
        default: 0,
        min: 0
    },
    totalSkips: {
        type: Number,
        default: 0,
        min: 0
    },
    
    // Autoplay preferences
    autoplayEnabled: {
        type: Boolean,
        default: true
    },
    recommendationSensitivity: {
        type: Number,
        min: 0,
        max: 1,
        default: 0.7
    },
    
    // Timestamps
    createdAt: {
        type: Date,
        default: Date.now
    },
    updatedAt: {
        type: Date,
        default: Date.now
    }
}, {
    timestamps: true
});

// Create compound index for faster lookups
userPreferenceSchema.index({ userId: 1, guildId: 1 }, { unique: true });

// Static method to find or create user preferences
userPreferenceSchema.statics.findOrCreate = async function(userId, guildId) {
    let userPref = await this.findOne({ userId, guildId });
    
    if (!userPref) {
        userPref = new this({
            userId,
            guildId,
            genrePreferences: new Map(),
            artistPreferences: new Map(),
            moodPreferences: new Map()
        });
        await userPref.save();
    }
    
    return userPref;
};

// Method to update genre preference
userPreferenceSchema.methods.updateGenrePreference = async function(genre, weight) {
    if (!this.genrePreferences) {
        this.genrePreferences = new Map();
    }
    
    const currentWeight = this.genrePreferences.get(genre) || 0;
    const newWeight = Math.max(0, Math.min(1, currentWeight + weight));
    
    this.genrePreferences.set(genre, newWeight);
    await this.save();
    return this;
};

// Method to update artist preference
userPreferenceSchema.methods.updateArtistPreference = async function(artist, weight) {
    if (!this.artistPreferences) {
        this.artistPreferences = new Map();
    }
    
    const currentWeight = this.artistPreferences.get(artist) || 0;
    const newWeight = Math.max(0, Math.min(1, currentWeight + weight));
    
    this.artistPreferences.set(artist, newWeight);
    await this.save();
    return this;
};

// Method to update mood preference
userPreferenceSchema.methods.updateMoodPreference = async function(mood, weight) {
    if (!this.moodPreferences) {
        this.moodPreferences = new Map();
    }
    
    const currentWeight = this.moodPreferences.get(mood) || 0;
    const newWeight = Math.max(0, Math.min(1, currentWeight + weight));
    
    this.moodPreferences.set(mood, newWeight);
    await this.save();
    return this;
};

// Method to record song interaction
userPreferenceSchema.methods.recordInteraction = async function(song, interactionType) {
    // Update basic statistics
    switch (interactionType) {
        case 'play':
            this.totalSongsPlayed += 1;
            this.totalListeningTime += Math.floor(song.duration / 60000); // Convert to minutes
            break;
        case 'like':
            this.totalLikes += 1;
            // Update preferences based on song attributes
            if (song.genre) {
                await this.updateGenrePreference(song.genre, 0.1);
            }
            if (song.artist) {
                await this.updateArtistPreference(song.artist, 0.1);
            }
            if (song.mood) {
                await this.updateMoodPreference(song.mood, 0.1);
            }
            break;
        case 'dislike':
            this.totalDislikes += 1;
            // Decrease preferences
            if (song.genre) {
                await this.updateGenrePreference(song.genre, -0.05);
            }
            if (song.artist) {
                await this.updateArtistPreference(song.artist, -0.05);
            }
            if (song.mood) {
                await this.updateMoodPreference(song.mood, -0.05);
            }
            break;
        case 'skip':
            this.totalSkips += 1;
            // Slight decrease in preferences
            if (song.genre) {
                await this.updateGenrePreference(song.genre, -0.02);
            }
            if (song.artist) {
                await this.updateArtistPreference(song.artist, -0.02);
            }
            break;
    }
    
    await this.save();
    return this;
};

// Method to get top preferred genres
userPreferenceSchema.methods.getTopGenres = function(limit = 5) {
    if (!this.genrePreferences) return [];
    
    return Array.from(this.genrePreferences.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, limit)
        .map(([genre, weight]) => ({ genre, weight }));
};

// Method to get top preferred artists
userPreferenceSchema.methods.getTopArtists = function(limit = 5) {
    if (!this.artistPreferences) return [];
    
    return Array.from(this.artistPreferences.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, limit)
        .map(([artist, weight]) => ({ artist, weight }));
};

// Pre-save hook to update timestamp
userPreferenceSchema.pre('save', function(next) {
    this.updatedAt = new Date();
    next();
});

// Create and export the model
const UserPreference = mongoose.model('UserPreference', userPreferenceSchema);
module.exports = UserPreference;
