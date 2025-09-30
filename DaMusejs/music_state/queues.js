/**
 * Queue Management System
 * 
 * This module handles music queue management for Discord voice channels.
 * It manages song queues, audio players, and playback state for each guild.
 * 
 * Features:
 * - Per-guild song queue management
 * - Audio player state tracking
 * - Queue manipulation (add, remove, clear)
 * - Playback state management
 * - Current song tracking
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// Queue management system - equivalent to music_state/queues.py
class QueueManager {
    /**
     * Constructor - Initialize the queue manager
     * 
     * Sets up storage for queues, players, and playback state per guild.
     */
    constructor() {
        this.queues = new Map(); // guildId -> queue array
        this.players = new Map(); // guildId -> audio player
        this.playing = new Map(); // guildId -> boolean
    }

    /**
     * Add To Queue
     * 
     * Adds a song to the queue for a specific guild.
     * 
     * @param {string} guildId - Guild ID
     * @param {Object} song - Song object to add to queue
     */
    addToQueue(guildId, song) {
        if (!this.queues.has(guildId)) {
            this.queues.set(guildId, []);
        }
        this.queues.get(guildId).push(song);
    }

    /**
     * Get Next Song
     * 
     * Retrieves and removes the next song from the queue (FIFO).
     * 
     * @param {string} guildId - Guild ID
     * @returns {Object|null} Next song or null if queue is empty
     */
    getNextSong(guildId) {
        const queue = this.queues.get(guildId);
        if (!queue || queue.length === 0) {
            return null;
        }
        return queue.shift();
    }

    /**
     * Get Queue
     * 
     * Returns the current queue for a guild.
     * 
     * @param {string} guildId - Guild ID
     * @returns {Array} Array of songs in queue
     */
    getQueue(guildId) {
        return this.queues.get(guildId) || [];
    }

    /**
     * Clear Queue
     * 
     * Removes all songs from the queue for a guild.
     * 
     * @param {string} guildId - Guild ID
     */
    clearQueue(guildId) {
        this.queues.set(guildId, []);
    }

    /**
     * Set Player
     * 
     * Associates an audio player with a guild.
     * 
     * @param {string} guildId - Guild ID
     * @param {Object} player - Audio player instance
     */
    setPlayer(guildId, player) {
        this.players.set(guildId, player);
    }

    /**
     * Get Player
     * 
     * Retrieves the audio player for a guild.
     * 
     * @param {string} guildId - Guild ID
     * @returns {Object|null} Audio player or null if not set
     */
    getPlayer(guildId) {
        return this.players.get(guildId);
    }

    /**
     * Set Playing
     * 
     * Updates the playback state for a guild.
     * 
     * @param {string} guildId - Guild ID
     * @param {boolean} isPlaying - Whether music is currently playing
     */
    setPlaying(guildId, isPlaying) {
        this.playing.set(guildId, isPlaying);
    }

    /**
     * Is Playing
     * 
     * Checks if music is currently playing in a guild.
     * 
     * @param {string} guildId - Guild ID
     * @returns {boolean} True if playing, false otherwise
     */
    isPlaying(guildId) {
        return this.playing.get(guildId) || false;
    }

    /**
     * Get Current Song
     * 
     * Returns the currently playing song (first in queue).
     * In a more sophisticated system, this would track the actual playing song.
     * 
     * @param {string} guildId - Guild ID
     * @returns {Object|null} Current song or null if no songs
     */
    getCurrentSong(guildId) {
        // For now, return the first song in queue as "current"
        // In a more sophisticated system, you'd track the currently playing song
        const queue = this.queues.get(guildId);
        if (!queue || queue.length === 0) {
            return null;
        }
        return queue[0]; // Return first song in queue
    }

    /**
     * Remove Guild
     * 
     * Cleans up all data for a guild when it's no longer needed.
     * 
     * @param {string} guildId - Guild ID to remove
     */
    removeGuild(guildId) {
        this.queues.delete(guildId);
        this.players.delete(guildId);
        this.playing.delete(guildId);
    }

    /**
     * Cleanup Connection
     * 
     * Cleans up a specific guild's connection and player.
     * 
     * @param {string} guildId - Guild ID to clean up
     */
    cleanupConnection(guildId) {
        console.log(`🧹 [QUEUE_CLEANUP] Cleaning up connection for guild ${guildId}...`);
        
        try {
            // Stop and remove player
            const player = this.players.get(guildId);
            if (player) {
                player.stop();
                console.log(`🧹 [QUEUE_CLEANUP] ✅ Stopped player for guild ${guildId}`);
            }
            
            // Clear guild data
            this.queues.delete(guildId);
            this.players.delete(guildId);
            this.playing.delete(guildId);
            
            console.log(`🧹 [QUEUE_CLEANUP] ✅ Cleaned up guild ${guildId}`);
        } catch (error) {
            console.error(`🧹 [QUEUE_CLEANUP] ❌ Failed to clean up guild ${guildId}:`, error);
        }
    }

    /**
     * Cleanup All Connections
     * 
     * Cleans up all voice connections and players for all guilds.
     * Used during bot shutdown or restart to prevent connection issues.
     */
    cleanupAllConnections() {
        console.log('🧹 [QUEUE_CLEANUP] Cleaning up all voice connections...');
        
        // Clean up all players
        for (const [guildId, player] of this.players) {
            try {
                if (player) {
                    player.stop();
                    console.log(`🧹 [QUEUE_CLEANUP] ✅ Stopped player for guild ${guildId}`);
                }
            } catch (error) {
                console.error(`🧹 [QUEUE_CLEANUP] ❌ Failed to stop player for guild ${guildId}:`, error);
            }
        }
        
        // Clear all data
        this.queues.clear();
        this.players.clear();
        this.playing.clear();
        
        console.log('🧹 [QUEUE_CLEANUP] ✅ All connections cleaned up');
    }
}

// Export as default like Python module
const queues = new QueueManager();
module.exports = { queues };
