/**
 * Mix Engine - Collaborative Music Mixing System
 * 
 * This module creates collaborative music mixes by analyzing multiple users'
 * preferences and generating balanced playlists. It supports different mixing
 * modes and ensures diversity in song selection.
 * 
 * Features:
 * - Collaborative mix generation for multiple users
 * - Multiple mix modes (balanced, popular, diverse)
 * - User preference weighting and analysis
 * - Diversity filtering and song selection
 * - Mix statistics and analytics
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// ⚠️  TEMPORARY: Using in-memory database models for testing
const Song = require('../models/tempSong');
const UserPreference = require('../models/tempUserPreference');
const MusicInteraction = require('../models/tempMusicInteraction');
const recommendationEngine = require('./recommendationEngine');

/**
 * Mix Engine Class
 * 
 * Handles collaborative music mix generation by analyzing user preferences
 * and creating balanced playlists that appeal to multiple users.
 */
class MixEngine {
    constructor() {
        this.mixModes = {
            balanced: {
                userWeight: 0.4,
                popularityWeight: 0.3,
                diversityWeight: 0.3
            },
            popular: {
                userWeight: 0.2,
                popularityWeight: 0.6,
                diversityWeight: 0.2
            },
            diverse: {
                userWeight: 0.3,
                popularityWeight: 0.2,
                diversityWeight: 0.5
            }
        };
    }

    /**
     * Create a collaborative mix for multiple users
     * @param {Array} userIds - Array of user IDs in the voice channel
     * @param {string} guildId - Guild ID
     * @param {number} count - Number of songs to include
     * @param {string} mode - Mix mode (balanced, popular, diverse)
     * @returns {Array} Array of recommended songs
     */
    async createCollaborativeMix(userIds, guildId, count = 10, mode = 'balanced') {
        try {
            console.log(`[MIX] Creating ${mode} mix for ${userIds.length} users`);

            // Get all user preferences
            const userPreferences = await this.getUserPreferences(userIds, guildId);
            
            // Get recent songs to avoid duplicates
            const recentSongs = await this.getRecentSongs(userIds, guildId);
            const recentSongIds = recentSongs.map(song => song._id);

            // Create collaborative recommendations
            const recommendations = await this.generateCollaborativeRecommendations(
                userPreferences,
                guildId,
                count * 2, // Get more than needed for filtering
                mode,
                recentSongIds
            );

            // Apply diversity filtering
            const diverseRecommendations = this.applyDiversityFilter(recommendations, count);

            console.log(`[MIX] Generated ${diverseRecommendations.length} songs for collaborative mix`);
            return diverseRecommendations;

        } catch (error) {
            console.error('[MIX] Error creating collaborative mix:', error);
            return [];
        }
    }

    /**
     * Get user preferences for all users
     * @param {Array} userIds - Array of user IDs
     * @param {string} guildId - Guild ID
     * @returns {Array} Array of user preferences
     */
    async getUserPreferences(userIds, guildId) {
        const preferences = [];
        
        for (const userId of userIds) {
            try {
                const userPref = await UserPreference.findOrCreate(userId, guildId);
                preferences.push({
                    userId,
                    preferences: userPref,
                    weight: 1.0 // Equal weight for all users initially
                });
            } catch (error) {
                console.error(`[MIX] Error getting preferences for user ${userId}:`, error);
            }
        }

        return preferences;
    }

    /**
     * Get recent songs played by any of the users
     * @param {Array} userIds - Array of user IDs
     * @param {string} guildId - Guild ID
     * @param {number} hours - Hours to look back
     * @returns {Array} Recent songs
     */
    async getRecentSongs(userIds, guildId, hours = 24) {
        const startTime = new Date(Date.now() - hours * 60 * 60 * 1000);
        
        const recentInteractions = await MusicInteraction.find({
            userId: { $in: userIds },
            guildId,
            playedAt: { $gte: startTime },
            interactionType: 'play'
        }).populate('songId');

        return recentInteractions.map(interaction => interaction.songId).filter(Boolean);
    }

    /**
     * Generate collaborative recommendations
     * @param {Array} userPreferences - Array of user preferences
     * @param {string} guildId - Guild ID
     * @param {number} count - Number of recommendations
     * @param {string} mode - Mix mode
     * @param {Array} excludeIds - Song IDs to exclude
     * @returns {Array} Recommended songs
     */
    async generateCollaborativeRecommendations(userPreferences, guildId, count, mode, excludeIds = []) {
        const weights = this.mixModes[mode] || this.mixModes.balanced;
        const allRecommendations = [];

        // Get individual recommendations for each user
        for (const userPref of userPreferences) {
            try {
                const userRecommendations = await recommendationEngine.getRecommendations(
                    userPref.userId,
                    guildId,
                    Math.ceil(count / userPreferences.length)
                );

                // Weight recommendations based on user activity
                const userWeight = this.calculateUserWeight(userPref.preferences);
                
                userRecommendations.forEach(rec => {
                    allRecommendations.push({
                        song: rec,
                        score: rec.recommendationScore * userWeight * weights.userWeight,
                        source: 'user',
                        userId: userPref.userId
                    });
                });
            } catch (error) {
                console.error(`[MIX] Error getting recommendations for user ${userPref.userId}:`, error);
            }
        }

        // Get popular songs for the guild
        if (weights.popularityWeight > 0) {
            try {
                const popularSongs = await recommendationEngine.getTrendingSongs(guildId, Math.ceil(count * 0.5), 7);
                
                popularSongs.forEach(song => {
                    allRecommendations.push({
                        song,
                        score: song.recommendationScore * weights.popularityWeight,
                        source: 'popular',
                        userId: null
                    });
                });
            } catch (error) {
                console.error('[MIX] Error getting popular songs:', error);
            }
        }

        // Filter out excluded songs and duplicates
        const filteredRecommendations = this.filterRecommendations(allRecommendations, excludeIds);
        
        // Sort by combined score
        return filteredRecommendations
            .sort((a, b) => b.score - a.score)
            .slice(0, count);
    }

    /**
     * Calculate user weight based on their activity
     * @param {Object} userPref - User preferences
     * @returns {number} User weight
     */
    calculateUserWeight(userPref) {
        const totalSongs = userPref.totalSongsPlayed || 0;
        const totalTime = userPref.totalListeningTime || 0;
        const interactions = (userPref.totalLikes || 0) + (userPref.totalDislikes || 0) + (userPref.totalSkips || 0);

        // Weight based on activity level
        let weight = 0.5; // Base weight
        
        if (totalSongs > 50) weight += 0.2;
        if (totalTime > 300) weight += 0.2; // 5+ hours
        if (interactions > 20) weight += 0.1;

        return Math.min(1.0, weight);
    }

    /**
     * Filter recommendations to remove duplicates and excluded songs
     * @param {Array} recommendations - All recommendations
     * @param {Array} excludeIds - Song IDs to exclude
     * @returns {Array} Filtered recommendations
     */
    filterRecommendations(recommendations, excludeIds) {
        const seen = new Set();
        const filtered = [];

        for (const rec of recommendations) {
            const songId = rec.song._id.toString();
            
            if (!seen.has(songId) && !excludeIds.includes(songId)) {
                seen.add(songId);
                filtered.push(rec);
            }
        }

        return filtered;
    }

    /**
     * Apply diversity filter to ensure variety in the mix
     * @param {Array} recommendations - Sorted recommendations
     * @param {number} count - Number of songs to return
     * @returns {Array} Diverse recommendations
     */
    applyDiversityFilter(recommendations, count) {
        if (recommendations.length <= count) {
            return recommendations.map(rec => rec.song);
        }

        const diverse = [];
        const usedGenres = new Set();
        const usedArtists = new Set();
        const usedUsers = new Set();

        // First pass: prioritize high-scoring songs with diversity
        for (const rec of recommendations) {
            if (diverse.length >= count) break;

            const song = rec.song;
            const genre = song.genre || 'Unknown';
            const artist = song.artist || 'Unknown';
            const userId = rec.userId;

            // Check diversity constraints
            const genreUsed = usedGenres.has(genre);
            const artistUsed = usedArtists.has(artist);
            const userUsed = userId && usedUsers.has(userId);

            // Allow some repetition but limit it
            const genreLimit = Math.ceil(count / 3); // Max 1/3 from same genre
            const artistLimit = Math.ceil(count / 5); // Max 1/5 from same artist
            const userLimit = Math.ceil(count / 2); // Max 1/2 from same user

            const genreCount = Array.from(usedGenres).filter(g => g === genre).length;
            const artistCount = Array.from(usedArtists).filter(a => a === artist).length;
            const userCount = Array.from(usedUsers).filter(u => u === userId).length;

            if (genreCount < genreLimit && artistCount < artistLimit && userCount < userLimit) {
                diverse.push(rec);
                usedGenres.add(genre);
                usedArtists.add(artist);
                if (userId) usedUsers.add(userId);
            }
        }

        // Second pass: fill remaining slots with best available songs
        if (diverse.length < count) {
            for (const rec of recommendations) {
                if (diverse.length >= count) break;
                
                const songId = rec.song._id.toString();
                const alreadyIncluded = diverse.some(d => d.song._id.toString() === songId);
                
                if (!alreadyIncluded) {
                    diverse.push(rec);
                }
            }
        }

        return diverse.map(rec => rec.song);
    }

    /**
     * Get mix statistics for a group of users
     * @param {Array} userIds - Array of user IDs
     * @param {string} guildId - Guild ID
     * @returns {Object} Mix statistics
     */
    async getMixStats(userIds, guildId) {
        try {
            const stats = {
                totalUsers: userIds.length,
                activeUsers: 0,
                totalSongsPlayed: 0,
                commonGenres: [],
                commonArtists: [],
                averageEnergy: 0,
                diversityScore: 0
            };

            // Get user preferences and calculate stats
            const userPreferences = await this.getUserPreferences(userIds, guildId);
            
            for (const userPref of userPreferences) {
                if (userPref.preferences.totalSongsPlayed > 0) {
                    stats.activeUsers++;
                    stats.totalSongsPlayed += userPref.preferences.totalSongsPlayed;
                }
            }

            // Get common genres and artists
            const genreStats = await this.getCommonGenres(userIds, guildId);
            const artistStats = await this.getCommonArtists(userIds, guildId);

            stats.commonGenres = genreStats.slice(0, 5);
            stats.commonArtists = artistStats.slice(0, 5);

            return stats;

        } catch (error) {
            console.error('[MIX] Error getting mix stats:', error);
            return {
                totalUsers: userIds.length,
                activeUsers: 0,
                totalSongsPlayed: 0,
                commonGenres: [],
                commonArtists: [],
                averageEnergy: 0,
                diversityScore: 0
            };
        }
    }

    /**
     * Get common genres among users
     * @param {Array} userIds - Array of user IDs
     * @param {string} guildId - Guild ID
     * @returns {Array} Common genres
     */
    async getCommonGenres(userIds, guildId) {
        const genreStats = await MusicInteraction.aggregate([
            { 
                $match: { 
                    userId: { $in: userIds }, 
                    guildId,
                    interactionType: 'like'
                } 
            },
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
            { $limit: 10 }
        ]);

        return genreStats.map(stat => ({
            genre: stat._id,
            count: stat.likeCount
        }));
    }

    /**
     * Get common artists among users
     * @param {Array} userIds - Array of user IDs
     * @param {string} guildId - Guild ID
     * @returns {Array} Common artists
     */
    async getCommonArtists(userIds, guildId) {
        const artistStats = await MusicInteraction.aggregate([
            { 
                $match: { 
                    userId: { $in: userIds }, 
                    guildId,
                    interactionType: 'like'
                } 
            },
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
                    _id: '$song.artist',
                    likeCount: { $sum: 1 }
                }
            },
            { $sort: { likeCount: -1 } },
            { $limit: 10 }
        ]);

        return artistStats.map(stat => ({
            artist: stat._id,
            count: stat.likeCount
        }));
    }
}

module.exports = new MixEngine();
