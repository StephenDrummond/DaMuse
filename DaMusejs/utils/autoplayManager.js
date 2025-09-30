/**
 * Autoplay Manager - Music Recommendation System
 * 
 * This module manages automatic music recommendations and playback.
 * It handles user preferences, recommendation generation, and autoplay
 * functionality for seamless music discovery.
 * 
 * Features:
 * - Per-guild autoplay state management
 * - User preference-based recommendations
 * - Trending song recommendations
 * - Weighted random song selection
 * - Autoplay statistics and analytics
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// ⚠️  TEMPORARY: Using in-memory database models for testing
const recommendationEngine = require('./recommendationEngine');
const Song = require('../models/tempSong');
const UserPreference = require('../models/tempUserPreference');
const MusicInteraction = require('../models/tempMusicInteraction');

/**
 * Autoplay Manager Class
 * 
 * Handles all autoplay functionality including recommendation generation,
 * user preference management, and automatic song selection.
 */
class AutoplayManager {
    constructor() {
        this.autoplayEnabled = new Map(); // guildId -> boolean
        this.autoplayUsers = new Map(); // guildId -> Set of userIds
        this.lastRecommendationTime = new Map(); // guildId -> timestamp
    }

    /**
     * Enable autoplay for a guild
     * @param {string} guildId - Guild ID
     * @param {string} userId - User who enabled autoplay
     */
    enableAutoplay(guildId, userId) {
        this.autoplayEnabled.set(guildId, true);
        
        if (!this.autoplayUsers.has(guildId)) {
            this.autoplayUsers.set(guildId, new Set());
        }
        this.autoplayUsers.get(guildId).add(userId);
        
        console.log(`[AUTOPLAY] Enabled for guild ${guildId} by user ${userId}`);
    }

    /**
     * Disable autoplay for a guild
     * @param {string} guildId - Guild ID
     */
    disableAutoplay(guildId) {
        this.autoplayEnabled.set(guildId, false);
        this.autoplayUsers.delete(guildId);
        this.lastRecommendationTime.delete(guildId);
        
        console.log(`[AUTOPLAY] Disabled for guild ${guildId}`);
    }

    /**
     * Check if autoplay is enabled for a guild
     * @param {string} guildId - Guild ID
     * @returns {boolean} Whether autoplay is enabled
     */
    isAutoplayEnabled(guildId) {
        return this.autoplayEnabled.get(guildId) || false;
    }

    /**
     * Get recommended songs for autoplay
     * @param {string} guildId - Guild ID
     * @param {number} count - Number of recommendations
     * @returns {Array} Recommended songs
     */
    async getAutoplayRecommendations(guildId, count = 5) {
        try {
            if (!this.isAutoplayEnabled(guildId)) {
                return [];
            }

            // Get all users who have enabled autoplay in this guild
            const users = this.autoplayUsers.get(guildId);
            if (!users || users.size === 0) {
                return [];
            }

            // Get recommendations for each user and combine them
            const allRecommendations = [];
            
            for (const userId of users) {
                const userPref = await UserPreference.findOrCreate(userId, guildId);
                
                if (userPref.autoplayEnabled) {
                    const recommendations = await recommendationEngine.getRecommendations(
                        userId, 
                        guildId, 
                        Math.ceil(count / users.size)
                    );
                    allRecommendations.push(...recommendations);
                }
            }

            // Remove duplicates and return top recommendations
            const uniqueRecommendations = this.removeDuplicateSongs(allRecommendations);
            return uniqueRecommendations.slice(0, count);

        } catch (error) {
            console.error('[AUTOPLAY] Error getting recommendations:', error);
            return [];
        }
    }

    /**
     * Get trending songs for autoplay when user preferences are insufficient
     * @param {string} guildId - Guild ID
     * @param {number} count - Number of trending songs
     * @returns {Array} Trending songs
     */
    async getTrendingRecommendations(guildId, count = 5) {
        try {
            const trendingSongs = await recommendationEngine.getTrendingSongs(guildId, count, 7);
            return trendingSongs;

        } catch (error) {
            console.error('[AUTOPLAY] Error getting trending recommendations:', error);
            return [];
        }
    }

    /**
     * Get the next song for autoplay
     * @param {string} guildId - Guild ID
     * @param {string} currentSongId - Current song ID (to avoid duplicates)
     * @returns {Object|null} Next song or null
     */
    async getNextAutoplaySong(guildId, currentSongId = null) {
        try {
            if (!this.isAutoplayEnabled(guildId)) {
                return null;
            }

            // Check if we should wait before recommending again
            const lastRecTime = this.lastRecommendationTime.get(guildId);
            const now = Date.now();
            const minInterval = 30 * 1000; // 30 seconds minimum between recommendations

            if (lastRecTime && (now - lastRecTime) < minInterval) {
                return null;
            }

            // Get recommendations
            let recommendations = await this.getAutoplayRecommendations(guildId, 10);
            
            // If no personalized recommendations, try trending songs
            if (recommendations.length === 0) {
                recommendations = await this.getTrendingRecommendations(guildId, 10);
            }

            // Filter out current song if provided
            if (currentSongId) {
                recommendations = recommendations.filter(song => song._id.toString() !== currentSongId);
            }

            if (recommendations.length === 0) {
                return null;
            }

            // Select a random song from top recommendations (weighted by score)
            const selectedSong = this.selectWeightedRandomSong(recommendations);
            
            // Update recommendation time
            this.lastRecommendationTime.set(guildId, now);

            return selectedSong;

        } catch (error) {
            console.error('[AUTOPLAY] Error getting next song:', error);
            return null;
        }
    }

    /**
     * Record that a song was played via autoplay
     * @param {string} guildId - Guild ID
     * @param {string} songId - Song ID
     * @param {string} userId - User ID (primary user who enabled autoplay)
     */
    async recordAutoplayPlay(songId, guildId, userId) {
        try {
            // Record the interaction
            await MusicInteraction.recordInteraction({
                userId,
                guildId,
                songId,
                interactionType: 'play',
                wasAutoplay: true,
                wasRecommended: true
            });

            // Update song play count
            const song = await Song.findById(songId);
            if (song) {
                await song.recordPlay();
            }

            // Update user preferences
            const userPref = await UserPreference.findOrCreate(userId, guildId);
            if (song) {
                await userPref.recordInteraction(song, 'play');
            }

        } catch (error) {
            console.error('[AUTOPLAY] Error recording autoplay play:', error);
        }
    }

    /**
     * Remove duplicate songs from recommendations
     * @param {Array} songs - Array of songs
     * @returns {Array} Unique songs
     */
    removeDuplicateSongs(songs) {
        const seen = new Set();
        return songs.filter(song => {
            const key = song._id.toString();
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        });
    }

    /**
     * Select a random song weighted by recommendation score
     * @param {Array} songs - Array of songs with scores
     * @returns {Object} Selected song
     */
    selectWeightedRandomSong(songs) {
        if (songs.length === 0) return null;
        if (songs.length === 1) return songs[0];

        // Calculate total weight
        const totalWeight = songs.reduce((sum, song) => sum + (song.score || 0.5), 0);
        
        // Generate random number
        let random = Math.random() * totalWeight;
        
        // Select song based on weight
        for (const song of songs) {
            random -= (song.score || 0.5);
            if (random <= 0) {
                return song;
            }
        }
        
        // Fallback to last song
        return songs[songs.length - 1];
    }

    /**
     * Get autoplay statistics for a guild
     * @param {string} guildId - Guild ID
     * @returns {Object} Autoplay statistics
     */
    async getAutoplayStats(guildId) {
        try {
            const stats = await MusicInteraction.aggregate([
                { 
                    $match: { 
                        guildId, 
                        wasAutoplay: true,
                        playedAt: { $gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) } // Last 7 days
                    } 
                },
                {
                    $group: {
                        _id: null,
                        totalAutoplayPlays: { $sum: 1 },
                        uniqueSongs: { $addToSet: '$songId' },
                        avgDuration: { $avg: '$duration' }
                    }
                }
            ]);

            const result = stats[0] || {
                totalAutoplayPlays: 0,
                uniqueSongs: [],
                avgDuration: 0
            };

            return {
                totalPlays: result.totalAutoplayPlays,
                uniqueSongsPlayed: result.uniqueSongs.length,
                averageDuration: Math.round(result.avgDuration / 1000), // Convert to seconds
                isEnabled: this.isAutoplayEnabled(guildId),
                activeUsers: this.autoplayUsers.get(guildId)?.size || 0
            };

        } catch (error) {
            console.error('[AUTOPLAY] Error getting stats:', error);
            return {
                totalPlays: 0,
                uniqueSongsPlayed: 0,
                averageDuration: 0,
                isEnabled: false,
                activeUsers: 0
            };
        }
    }

    /**
     * Clean up old autoplay data
     * This should be called periodically to clean up inactive guilds
     */
    cleanup() {
        const now = Date.now();
        const maxInactiveTime = 24 * 60 * 60 * 1000; // 24 hours

        for (const [guildId, lastTime] of this.lastRecommendationTime.entries()) {
            if (now - lastTime > maxInactiveTime) {
                this.autoplayEnabled.delete(guildId);
                this.autoplayUsers.delete(guildId);
                this.lastRecommendationTime.delete(guildId);
                console.log(`[AUTOPLAY] Cleaned up inactive guild ${guildId}`);
            }
        }
    }
}

module.exports = new AutoplayManager();
