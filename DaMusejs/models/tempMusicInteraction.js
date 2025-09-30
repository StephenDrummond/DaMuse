/**
 * TEMPORARY MUSIC INTERACTION MODEL - IN-MEMORY DATABASE
 * 
 * ⚠️  WARNING: THIS IS TEMPORARY CODE FOR TESTING PURPOSES ONLY ⚠️
 * 
 * This file provides a temporary MusicInteraction model that uses in-memory storage
 * instead of MongoDB. All data will be lost when the bot restarts.
 * 
 * TO CLEAN UP:
 * 1. Delete this file: models/tempMusicInteraction.js
 * 2. Restore original MusicInteraction.js from git
 * 3. Update imports in other files to use original MusicInteraction model
 */

const tempDb = require('../utils/tempDatabase');

class TempMusicInteraction {
    constructor(data) {
        Object.assign(this, data);
        this._id = data._id || tempDb.generateId('musicInteractions');
    }

    // Static methods
    static async recordInteraction(data) {
        const interaction = await tempDb.create('musicInteractions', data);
        return new TempMusicInteraction(interaction);
    }

    static async findOne(query) {
        const doc = await tempDb.findOne('musicInteractions', query);
        return doc ? new TempMusicInteraction(doc) : null;
    }

    static async find(query = {}, options = {}) {
        const docs = await tempDb.find('musicInteractions', query, options);
        return docs.map(doc => new TempMusicInteraction(doc));
    }

    static async findById(id) {
        const doc = await tempDb.findById('musicInteractions', id);
        return doc ? new TempMusicInteraction(doc) : null;
    }

    static async getUserHistory(userId, guildId, limit = 50) {
        const interactions = await tempDb.find('musicInteractions', 
            { userId, guildId }, 
            { sort: { playedAt: -1 }, limit }
        );
        
        // Simulate populate by fetching song data
        const populatedInteractions = [];
        for (const interaction of interactions) {
            const song = await tempDb.findById('songs', interaction.songId);
            populatedInteractions.push({
                ...interaction,
                songId: song ? new TempSong(song) : interaction.songId
            });
        }
        
        return populatedInteractions.map(doc => new TempMusicInteraction(doc));
    }

    static async getSongStats(songId, timeRange = null) {
        let query = { songId };
        
        if (timeRange) {
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - timeRange);
            query.playedAt = { $gte: startDate };
        }
        
        const interactions = await tempDb.find('musicInteractions', query);
        
        // Group by interaction type and calculate stats
        const stats = {};
        for (const interaction of interactions) {
            const type = interaction.interactionType;
            if (!stats[type]) {
                stats[type] = { count: 0, totalDuration: 0 };
            }
            stats[type].count += 1;
            stats[type].totalDuration += interaction.duration || 0;
        }
        
        // Convert to array format similar to MongoDB aggregate
        return Object.entries(stats).map(([interactionType, data]) => ({
            _id: interactionType,
            count: data.count,
            avgDuration: data.count > 0 ? data.totalDuration / data.count : 0
        }));
    }

    static async getPopularSongs(guildId, limit = 20, timeRange = 7) {
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - timeRange);
        
        const interactions = await tempDb.find('musicInteractions', {
            guildId,
            playedAt: { $gte: startDate },
            interactionType: 'play'
        });
        
        // Group by songId and count plays
        const songStats = {};
        for (const interaction of interactions) {
            const songId = interaction.songId;
            if (!songStats[songId]) {
                songStats[songId] = { playCount: 0, totalDuration: 0 };
            }
            songStats[songId].playCount += 1;
            songStats[songId].totalDuration += interaction.duration || 0;
        }
        
        // Sort by play count and get top songs
        const sortedSongs = Object.entries(songStats)
            .sort((a, b) => b[1].playCount - a[1].playCount)
            .slice(0, limit);
        
        // Fetch song data and format results
        const results = [];
        for (const [songId, stats] of sortedSongs) {
            const song = await tempDb.findById('songs', songId);
            if (song) {
                results.push({
                    _id: songId,
                    playCount: stats.playCount,
                    avgDuration: stats.playCount > 0 ? stats.totalDuration / stats.playCount : 0,
                    song: song
                });
            }
        }
        
        return results;
    }

    static async getUserFavoriteGenres(userId, guildId, limit = 10) {
        const likedInteractions = await tempDb.find('musicInteractions', {
            userId,
            guildId,
            interactionType: 'like'
        });
        
        // Get song data for liked interactions
        const genreCounts = {};
        for (const interaction of likedInteractions) {
            const song = await tempDb.findById('songs', interaction.songId);
            if (song && song.genre) {
                genreCounts[song.genre] = (genreCounts[song.genre] || 0) + 1;
            }
        }
        
        // Sort by count and return top genres
        return Object.entries(genreCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit)
            .map(([genre, likeCount]) => ({ _id: genre, likeCount }));
    }

    // Instance methods
    async save() {
        const data = { ...this };
        delete data._id; // Remove _id from data to avoid duplication
        
        if (this._id && await tempDb.findById('musicInteractions', this._id)) {
            // Update existing
            await tempDb.updateOne('musicInteractions', { _id: this._id }, data);
        } else {
            // Create new
            const newDoc = await tempDb.create('musicInteractions', data);
            this._id = newDoc._id;
            Object.assign(this, newDoc);
        }
        return this;
    }

    async markComplete(duration) {
        this.interactionType = 'complete';
        this.duration = duration;
        await this.save();
        return this;
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

// Import TempSong for type reference (circular dependency handled)
const TempSong = require('./tempSong');

module.exports = TempMusicInteraction;
