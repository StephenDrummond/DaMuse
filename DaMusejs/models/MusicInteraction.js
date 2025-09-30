const mongoose = require('mongoose');

// Define the schema for music interactions
const musicInteractionSchema = new mongoose.Schema({
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
    songId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Song',
        required: true,
        index: true
    },
    
    // Interaction details
    interactionType: {
        type: String,
        enum: ['play', 'like', 'dislike', 'skip', 'complete'],
        required: true,
        index: true
    },
    
    // Context information
    playedAt: {
        type: Date,
        default: Date.now,
        index: true
    },
    duration: {
        type: Number, // How long the song was played (in milliseconds)
        default: 0
    },
    position: {
        type: Number, // Position in queue when played
        default: 0
    },
    
    // Additional metadata
    wasAutoplay: {
        type: Boolean,
        default: false
    },
    wasRecommended: {
        type: Boolean,
        default: false
    },
    
    // Timestamps
    createdAt: {
        type: Date,
        default: Date.now
    }
}, {
    timestamps: true
});

// Create compound indexes for better performance
musicInteractionSchema.index({ userId: 1, guildId: 1, playedAt: -1 });
musicInteractionSchema.index({ songId: 1, interactionType: 1 });
musicInteractionSchema.index({ playedAt: -1 });

// Static method to record an interaction
musicInteractionSchema.statics.recordInteraction = async function(data) {
    const interaction = new this(data);
    await interaction.save();
    return interaction;
};

// Static method to get user's listening history
musicInteractionSchema.statics.getUserHistory = async function(userId, guildId, limit = 50) {
    return await this.find({ userId, guildId })
        .populate('songId')
        .sort({ playedAt: -1 })
        .limit(limit);
};

// Static method to get song interaction statistics
musicInteractionSchema.statics.getSongStats = async function(songId, timeRange = null) {
    const query = { songId };
    
    if (timeRange) {
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - timeRange);
        query.playedAt = { $gte: startDate };
    }
    
    const stats = await this.aggregate([
        { $match: query },
        {
            $group: {
                _id: '$interactionType',
                count: { $sum: 1 },
                avgDuration: { $avg: '$duration' }
            }
        }
    ]);
    
    return stats;
};

// Static method to get popular songs in a guild
musicInteractionSchema.statics.getPopularSongs = async function(guildId, limit = 20, timeRange = 7) {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - timeRange);
    
    return await this.aggregate([
        { 
            $match: { 
                guildId, 
                playedAt: { $gte: startDate },
                interactionType: 'play'
            } 
        },
        {
            $group: {
                _id: '$songId',
                playCount: { $sum: 1 },
                avgDuration: { $avg: '$duration' }
            }
        },
        { $sort: { playCount: -1 } },
        { $limit: limit },
        {
            $lookup: {
                from: 'songs',
                localField: '_id',
                foreignField: '_id',
                as: 'song'
            }
        },
        { $unwind: '$song' }
    ]);
};

// Static method to get user's favorite genres
musicInteractionSchema.statics.getUserFavoriteGenres = async function(userId, guildId, limit = 10) {
    return await this.aggregate([
        { $match: { userId, guildId, interactionType: 'like' } },
        {
            $lookup: {
                from: 'songs',
                localField: 'songId',
                foreignField: '_id',
                as: 'song'
            }
        },
        { $unwind: '$song' },
        {
            $group: {
                _id: '$song.genre',
                likeCount: { $sum: 1 }
            }
        },
        { $sort: { likeCount: -1 } },
        { $limit: limit }
    ]);
};

// Method to mark interaction as complete
musicInteractionSchema.methods.markComplete = async function(duration) {
    this.interactionType = 'complete';
    this.duration = duration;
    await this.save();
    return this;
};

// Create and export the model
const MusicInteraction = mongoose.model('MusicInteraction', musicInteractionSchema);
module.exports = MusicInteraction;
