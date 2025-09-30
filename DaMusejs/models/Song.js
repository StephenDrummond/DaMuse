const mongoose = require('mongoose');

// Define the schema for songs
const songSchema = new mongoose.Schema({
    // Basic song information
    title: {
        type: String,
        required: true,
        index: true
    },
    artist: {
        type: String,
        required: true,
        index: true
    },
    url: {
        type: String,
        required: true,
        unique: true
    },
    thumbnail: {
        type: String,
        default: null
    },
    duration: {
        type: Number, // Duration in milliseconds
        required: true
    },
    
    // Genre and categorization
    genre: {
        type: String,
        index: true,
        default: 'Unknown'
    },
    subgenre: {
        type: String,
        index: true,
        default: null
    },
    mood: {
        type: String,
        index: true,
        default: 'Neutral'
    },
    energy: {
        type: Number, // 1-10 scale
        min: 1,
        max: 10,
        default: 5
    },
    
    // YouTube/Spotify metadata
    youtubeId: {
        type: String,
        index: true
    },
    spotifyId: {
        type: String,
        index: true
    },
    
    // User interaction data
    playCount: {
        type: Number,
        default: 0,
        min: 0
    },
    likeCount: {
        type: Number,
        default: 0,
        min: 0
    },
    dislikeCount: {
        type: Number,
        default: 0,
        min: 0
    },
    skipCount: {
        type: Number,
        default: 0,
        min: 0
    },
    
    // Recommendation scores
    recommendationScore: {
        type: Number,
        default: 0.5,
        min: 0,
        max: 1
    },
    
    // Timestamps
    firstPlayed: {
        type: Date,
        default: null
    },
    lastPlayed: {
        type: Date,
        default: null
    },
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

// Create indexes for better performance
songSchema.index({ title: 'text', artist: 'text' }); // Text search
songSchema.index({ genre: 1, energy: 1 }); // Compound index for recommendations
songSchema.index({ playCount: -1 }); // Popular songs
songSchema.index({ recommendationScore: -1 }); // Best recommendations

// Static method to find or create a song
songSchema.statics.findOrCreate = async function(songData) {
    let song = await this.findOne({ url: songData.url });
    
    if (!song) {
        song = new this(songData);
        await song.save();
    }
    
    return song;
};

// Method to update play statistics
songSchema.methods.recordPlay = async function() {
    this.playCount += 1;
    this.lastPlayed = new Date();
    
    if (!this.firstPlayed) {
        this.firstPlayed = new Date();
    }
    
    await this.save();
    return this;
};

// Method to record user interaction
songSchema.methods.recordInteraction = async function(interactionType) {
    switch (interactionType) {
        case 'like':
            this.likeCount += 1;
            this.recommendationScore = Math.min(1, this.recommendationScore + 0.1);
            break;
        case 'dislike':
            this.dislikeCount += 1;
            this.recommendationScore = Math.max(0, this.recommendationScore - 0.1);
            break;
        case 'skip':
            this.skipCount += 1;
            this.recommendationScore = Math.max(0, this.recommendationScore - 0.05);
            break;
    }
    
    await this.save();
    return this;
};

// Method to get recommendation score based on various factors
songSchema.methods.calculateRecommendationScore = function() {
    const playWeight = Math.log(this.playCount + 1) * 0.3;
    const likeWeight = this.likeCount * 0.4;
    const dislikeWeight = this.dislikeCount * -0.3;
    const skipWeight = this.skipCount * -0.1;
    
    const baseScore = 0.5;
    const calculatedScore = baseScore + playWeight + likeWeight + dislikeWeight + skipWeight;
    
    return Math.max(0, Math.min(1, calculatedScore));
};

// Pre-save hook to update recommendation score
songSchema.pre('save', function(next) {
    this.recommendationScore = this.calculateRecommendationScore();
    this.updatedAt = new Date();
    next();
});

// Create and export the model
const Song = mongoose.model('Song', songSchema);
module.exports = Song;
