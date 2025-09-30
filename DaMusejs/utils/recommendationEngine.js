/**
 * Recommendation Engine - Personalized Music Recommendations
 * 
 * This module provides intelligent music recommendations based on user
 * preferences, listening history, and music attributes. It uses machine
 * learning-inspired algorithms to suggest relevant songs.
 * 
 * Features:
 * - Personalized recommendations based on user preferences
 * - Multi-factor scoring (genre, artist, mood, energy, popularity)
 * - Similar song recommendations
 * - Trending song discovery
 * - User taste profile analysis
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// ⚠️  TEMPORARY: Using in-memory database models for testing
const Song = require('../models/tempSong');
const UserPreference = require('../models/tempUserPreference');
const MusicInteraction = require('../models/tempMusicInteraction');

/**
 * Recommendation Engine Class
 * 
 * Generates personalized music recommendations using advanced algorithms
 * that analyze user preferences and music attributes.
 */
class RecommendationEngine {
    constructor() {
        this.weights = {
            genre: 0.3,
            artist: 0.25,
            mood: 0.2,
            energy: 0.15,
            popularity: 0.1
        };
    }

    /**
     * Get personalized recommendations for a user
     * @param {string} userId - User ID
     * @param {string} guildId - Guild ID
     * @param {number} limit - Number of recommendations
     * @returns {Array} Array of recommended songs
     */
    async getRecommendations(userId, guildId, limit = 10) {
        try {
            // Get user preferences
            const userPref = await UserPreference.findOrCreate(userId, guildId);
            
            // Get user's listening history to avoid recommending recent songs
            const recentSongs = await MusicInteraction.find({
                userId,
                guildId,
                playedAt: { $gte: new Date(Date.now() - 24 * 60 * 60 * 1000) } // Last 24 hours
            }).select('songId');

            const recentSongIds = recentSongs.map(interaction => interaction.songId);

            // Build recommendation query
            const query = this.buildRecommendationQuery(userPref, recentSongIds);
            
            // Get recommendations
            const recommendations = await Song.find(query)
                .sort({ recommendationScore: -1, playCount: -1 })
                .limit(limit * 2); // Get more than needed for filtering

            // Score and rank recommendations
            const scoredRecommendations = await this.scoreRecommendations(recommendations, userPref);
            
            // Return top recommendations
            return scoredRecommendations
                .sort((a, b) => b.score - a.score)
                .slice(0, limit)
                .map(rec => rec.song);

        } catch (error) {
            console.error('[RECOMMENDATION] Error getting recommendations:', error);
            return [];
        }
    }

    /**
     * Build MongoDB query based on user preferences
     * @param {Object} userPref - User preferences
     * @param {Array} recentSongIds - Recently played song IDs
     * @returns {Object} MongoDB query
     */
    buildRecommendationQuery(userPref, recentSongIds) {
        const query = {
            _id: { $nin: recentSongIds }, // Exclude recently played songs
            playCount: { $gte: 1 } // Only recommend songs that have been played at least once
        };

        // Add genre filter if user has strong genre preferences
        const topGenres = userPref.getTopGenres(3);
        if (topGenres.length > 0 && topGenres[0].weight > 0.3) {
            query.genre = { $in: topGenres.map(g => g.genre) };
        }

        // Add energy range filter
        if (userPref.preferredEnergyRange) {
            query.energy = {
                $gte: userPref.preferredEnergyRange.min,
                $lte: userPref.preferredEnergyRange.max
            };
        }

        return query;
    }

    /**
     * Score recommendations based on user preferences
     * @param {Array} songs - Songs to score
     * @param {Object} userPref - User preferences
     * @returns {Array} Scored recommendations
     */
    async scoreRecommendations(songs, userPref) {
        return songs.map(song => {
            let score = 0;

            // Genre score
            if (song.genre && userPref.genrePreferences.has(song.genre)) {
                score += this.weights.genre * userPref.genrePreferences.get(song.genre);
            }

            // Artist score
            if (song.artist && userPref.artistPreferences.has(song.artist)) {
                score += this.weights.artist * userPref.artistPreferences.get(song.artist);
            }

            // Mood score
            if (song.mood && userPref.moodPreferences.has(song.mood)) {
                score += this.weights.mood * userPref.moodPreferences.get(song.mood);
            }

            // Energy score
            const energyScore = this.calculateEnergyScore(song.energy, userPref.preferredEnergyRange);
            score += this.weights.energy * energyScore;

            // Popularity score (based on play count and likes)
            const popularityScore = this.calculatePopularityScore(song);
            score += this.weights.popularity * popularityScore;

            // Base recommendation score from the song
            score += song.recommendationScore * 0.2;

            return {
                song,
                score: Math.max(0, Math.min(1, score))
            };
        });
    }

    /**
     * Calculate energy score based on user's preferred energy range
     * @param {number} songEnergy - Song's energy level
     * @param {Object} preferredRange - User's preferred energy range
     * @returns {number} Energy score (0-1)
     */
    calculateEnergyScore(songEnergy, preferredRange) {
        if (!preferredRange) return 0.5;

        const { min, max } = preferredRange;
        
        if (songEnergy >= min && songEnergy <= max) {
            return 1.0; // Perfect match
        } else if (songEnergy < min) {
            return Math.max(0, 1 - (min - songEnergy) / 5); // Penalty for being too low
        } else {
            return Math.max(0, 1 - (songEnergy - max) / 5); // Penalty for being too high
        }
    }

    /**
     * Calculate popularity score based on song metrics
     * @param {Object} song - Song object
     * @returns {number} Popularity score (0-1)
     */
    calculatePopularityScore(song) {
        const playCount = song.playCount || 0;
        const likeCount = song.likeCount || 0;
        const dislikeCount = song.dislikeCount || 0;
        const skipCount = song.skipCount || 0;

        // Calculate like ratio
        const totalInteractions = likeCount + dislikeCount + skipCount;
        const likeRatio = totalInteractions > 0 ? likeCount / totalInteractions : 0.5;

        // Calculate play popularity (logarithmic scale)
        const playScore = Math.log(playCount + 1) / Math.log(1000); // Normalize to 0-1

        return (likeRatio * 0.7 + playScore * 0.3);
    }

    /**
     * Get similar songs based on a reference song
     * @param {string} songId - Reference song ID
     * @param {number} limit - Number of similar songs
     * @returns {Array} Similar songs
     */
    async getSimilarSongs(songId, limit = 10) {
        try {
            const referenceSong = await Song.findById(songId);
            if (!referenceSong) return [];

            const query = {
                _id: { $ne: songId },
                genre: referenceSong.genre,
                energy: {
                    $gte: Math.max(1, referenceSong.energy - 2),
                    $lte: Math.min(10, referenceSong.energy + 2)
                }
            };

            const similarSongs = await Song.find(query)
                .sort({ recommendationScore: -1 })
                .limit(limit);

            return similarSongs;

        } catch (error) {
            console.error('[RECOMMENDATION] Error getting similar songs:', error);
            return [];
        }
    }

    /**
     * Get trending songs in a guild
     * @param {string} guildId - Guild ID
     * @param {number} limit - Number of trending songs
     * @param {number} timeRange - Time range in days
     * @returns {Array} Trending songs
     */
    async getTrendingSongs(guildId, limit = 10, timeRange = 7) {
        try {
            const trendingSongs = await MusicInteraction.getPopularSongs(guildId, limit, timeRange);
            return trendingSongs.map(item => item.song);

        } catch (error) {
            console.error('[RECOMMENDATION] Error getting trending songs:', error);
            return [];
        }
    }

    /**
     * Update recommendation scores for all songs
     * This should be run periodically to keep scores up to date
     */
    async updateAllRecommendationScores() {
        try {
            console.log('[RECOMMENDATION] Updating recommendation scores...');
            
            const songs = await Song.find({});
            let updatedCount = 0;

            for (const song of songs) {
                const newScore = song.calculateRecommendationScore();
                if (Math.abs(newScore - song.recommendationScore) > 0.01) {
                    song.recommendationScore = newScore;
                    await song.save();
                    updatedCount++;
                }
            }

            console.log(`[RECOMMENDATION] Updated ${updatedCount} song scores`);
            return updatedCount;

        } catch (error) {
            console.error('[RECOMMENDATION] Error updating recommendation scores:', error);
            return 0;
        }
    }

    /**
     * Get user's music taste profile
     * @param {string} userId - User ID
     * @param {string} guildId - Guild ID
     * @returns {Object} User's music taste profile
     */
    async getUserTasteProfile(userId, guildId) {
        try {
            const userPref = await UserPreference.findOrCreate(userId, guildId);
            const favoriteGenres = await MusicInteraction.getUserFavoriteGenres(userId, guildId, 5);
            const recentHistory = await MusicInteraction.getUserHistory(userId, guildId, 20);

            return {
                preferences: userPref,
                favoriteGenres: favoriteGenres,
                recentHistory: recentHistory,
                totalSongsPlayed: userPref.totalSongsPlayed,
                totalListeningTime: userPref.totalListeningTime,
                topGenres: userPref.getTopGenres(5),
                topArtists: userPref.getTopArtists(5)
            };

        } catch (error) {
            console.error('[RECOMMENDATION] Error getting user taste profile:', error);
            return null;
        }
    }
}

module.exports = new RecommendationEngine();
