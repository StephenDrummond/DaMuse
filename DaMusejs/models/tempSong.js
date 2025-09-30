/**
 * TEMPORARY SONG MODEL - IN-MEMORY DATABASE
 * 
 * ⚠️  WARNING: THIS IS TEMPORARY CODE FOR TESTING PURPOSES ONLY ⚠️
 * 
 * This file provides a temporary Song model that uses in-memory storage
 * instead of MongoDB. All data will be lost when the bot restarts.
 * 
 * TO CLEAN UP:
 * 1. Delete this file: models/tempSong.js
 * 2. Restore original Song.js from git
 * 3. Update imports in other files to use original Song model
 */

const tempDb = require('../utils/tempDatabase');

class TempSong {
    constructor(data) {
        Object.assign(this, data);
        this._id = data._id || tempDb.generateId('songs');
    }

    // Static methods
    static async findOrCreate(songData) {
        let song = await tempDb.findOne('songs', { url: songData.url });
        
        if (!song) {
            song = await tempDb.create('songs', songData);
        }
        
        return new TempSong(song);
    }

    static async findOne(query) {
        const doc = await tempDb.findOne('songs', query);
        return doc ? new TempSong(doc) : null;
    }

    static async find(query = {}, options = {}) {
        const docs = await tempDb.find('songs', query, options);
        return docs.map(doc => new TempSong(doc));
    }

    static async findById(id) {
        const doc = await tempDb.findById('songs', id);
        return doc ? new TempSong(doc) : null;
    }

    // Instance methods
    async save() {
        const data = { ...this };
        delete data._id; // Remove _id from data to avoid duplication
        
        if (this._id && await tempDb.findById('songs', this._id)) {
            // Update existing
            await tempDb.updateOne('songs', { _id: this._id }, data);
        } else {
            // Create new
            const newDoc = await tempDb.create('songs', data);
            this._id = newDoc._id;
            Object.assign(this, newDoc);
        }
        return this;
    }

    async recordPlay() {
        this.playCount = (this.playCount || 0) + 1;
        this.lastPlayed = new Date();
        
        if (!this.firstPlayed) {
            this.firstPlayed = new Date();
        }
        
        await this.save();
        return this;
    }

    async recordInteraction(interactionType) {
        switch (interactionType) {
            case 'like':
                this.likeCount = (this.likeCount || 0) + 1;
                this.recommendationScore = Math.min(1, (this.recommendationScore || 0.5) + 0.1);
                break;
            case 'dislike':
                this.dislikeCount = (this.dislikeCount || 0) + 1;
                this.recommendationScore = Math.max(0, (this.recommendationScore || 0.5) - 0.1);
                break;
            case 'skip':
                this.skipCount = (this.skipCount || 0) + 1;
                this.recommendationScore = Math.max(0, (this.recommendationScore || 0.5) - 0.05);
                break;
        }
        
        await this.save();
        return this;
    }

    calculateRecommendationScore() {
        const playWeight = Math.log((this.playCount || 0) + 1) * 0.3;
        const likeWeight = (this.likeCount || 0) * 0.4;
        const dislikeWeight = (this.dislikeCount || 0) * -0.3;
        const skipWeight = (this.skipCount || 0) * -0.1;
        
        const baseScore = 0.5;
        const calculatedScore = baseScore + playWeight + likeWeight + dislikeWeight + skipWeight;
        
        return Math.max(0, Math.min(1, calculatedScore));
    }

    // Pre-save hook simulation
    async preSave() {
        this.recommendationScore = this.calculateRecommendationScore();
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

module.exports = TempSong;
