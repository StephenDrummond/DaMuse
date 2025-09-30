/**
 * TEMPORARY USER PREFERENCE MODEL - IN-MEMORY DATABASE
 * 
 * ⚠️  WARNING: THIS IS TEMPORARY CODE FOR TESTING PURPOSES ONLY ⚠️
 * 
 * This file provides a temporary UserPreference model that uses in-memory storage
 * instead of MongoDB. All data will be lost when the bot restarts.
 * 
 * TO CLEAN UP:
 * 1. Delete this file: models/tempUserPreference.js
 * 2. Restore original UserPreference.js from git
 * 3. Update imports in other files to use original UserPreference model
 */

const tempDb = require('../utils/tempDatabase');

class TempUserPreference {
    constructor(data) {
        Object.assign(this, data);
        this._id = data._id || tempDb.generateId('userPreferences');
    }

    // Static methods
    static async findOrCreate(userId, guildId) {
        let userPref = await tempDb.findOne('userPreferences', { userId, guildId });
        
        if (!userPref) {
            userPref = await tempDb.create('userPreferences', {
                userId,
                guildId,
                genrePreferences: new Map(),
                artistPreferences: new Map(),
                moodPreferences: new Map()
            });
        }
        
        return new TempUserPreference(userPref);
    }

    static async findOne(query) {
        const doc = await tempDb.findOne('userPreferences', query);
        return doc ? new TempUserPreference(doc) : null;
    }

    static async find(query = {}, options = {}) {
        const docs = await tempDb.find('userPreferences', query, options);
        return docs.map(doc => new TempUserPreference(doc));
    }

    static async findById(id) {
        const doc = await tempDb.findById('userPreferences', id);
        return doc ? new TempUserPreference(doc) : null;
    }

    // Instance methods
    async save() {
        const data = { ...this };
        delete data._id; // Remove _id from data to avoid duplication
        
        if (this._id && await tempDb.findById('userPreferences', this._id)) {
            // Update existing
            await tempDb.updateOne('userPreferences', { _id: this._id }, data);
        } else {
            // Create new
            const newDoc = await tempDb.create('userPreferences', data);
            this._id = newDoc._id;
            Object.assign(this, newDoc);
        }
        return this;
    }

    async updateGenrePreference(genre, weight) {
        if (!this.genrePreferences) {
            this.genrePreferences = new Map();
        }
        
        // Convert Map to Object for storage, then back to Map
        if (typeof this.genrePreferences === 'object' && !(this.genrePreferences instanceof Map)) {
            this.genrePreferences = new Map(Object.entries(this.genrePreferences));
        }
        
        const currentWeight = this.genrePreferences.get(genre) || 0;
        const newWeight = Math.max(0, Math.min(1, currentWeight + weight));
        
        this.genrePreferences.set(genre, newWeight);
        await this.save();
        return this;
    }

    async updateArtistPreference(artist, weight) {
        if (!this.artistPreferences) {
            this.artistPreferences = new Map();
        }
        
        // Convert Map to Object for storage, then back to Map
        if (typeof this.artistPreferences === 'object' && !(this.artistPreferences instanceof Map)) {
            this.artistPreferences = new Map(Object.entries(this.artistPreferences));
        }
        
        const currentWeight = this.artistPreferences.get(artist) || 0;
        const newWeight = Math.max(0, Math.min(1, currentWeight + weight));
        
        this.artistPreferences.set(artist, newWeight);
        await this.save();
        return this;
    }

    async updateMoodPreference(mood, weight) {
        if (!this.moodPreferences) {
            this.moodPreferences = new Map();
        }
        
        // Convert Map to Object for storage, then back to Map
        if (typeof this.moodPreferences === 'object' && !(this.moodPreferences instanceof Map)) {
            this.moodPreferences = new Map(Object.entries(this.moodPreferences));
        }
        
        const currentWeight = this.moodPreferences.get(mood) || 0;
        const newWeight = Math.max(0, Math.min(1, currentWeight + weight));
        
        this.moodPreferences.set(mood, newWeight);
        await this.save();
        return this;
    }

    async recordInteraction(song, interactionType) {
        // Update basic statistics
        switch (interactionType) {
            case 'play':
                this.totalSongsPlayed = (this.totalSongsPlayed || 0) + 1;
                this.totalListeningTime = (this.totalListeningTime || 0) + Math.floor(song.duration / 60000); // Convert to minutes
                break;
            case 'like':
                this.totalLikes = (this.totalLikes || 0) + 1;
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
                this.totalDislikes = (this.totalDislikes || 0) + 1;
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
                this.totalSkips = (this.totalSkips || 0) + 1;
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
    }

    getTopGenres(limit = 5) {
        if (!this.genrePreferences) return [];
        
        // Convert Map to Object for storage, then back to Map
        let preferences = this.genrePreferences;
        if (typeof this.genrePreferences === 'object' && !(this.genrePreferences instanceof Map)) {
            preferences = new Map(Object.entries(this.genrePreferences));
        }
        
        return Array.from(preferences.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit)
            .map(([genre, weight]) => ({ genre, weight }));
    }

    getTopArtists(limit = 5) {
        if (!this.artistPreferences) return [];
        
        // Convert Map to Object for storage, then back to Map
        let preferences = this.artistPreferences;
        if (typeof this.artistPreferences === 'object' && !(this.artistPreferences instanceof Map)) {
            preferences = new Map(Object.entries(this.artistPreferences));
        }
        
        return Array.from(preferences.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit)
            .map(([artist, weight]) => ({ artist, weight }));
    }

    // Pre-save hook simulation
    async preSave() {
        this.updatedAt = new Date();
    }

    // Convert to JSON (for compatibility)
    toJSON() {
        return { ...this };
    }

    // Convert to Object (for compatibility)
    toObject() {
        return { ...this };
    }
}

module.exports = TempUserPreference;
