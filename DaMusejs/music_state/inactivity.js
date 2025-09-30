/**
 * Inactivity Management System
 * 
 * This module handles automatic disconnection from voice channels when
 * there's no music activity. It prevents the bot from staying connected
 * indefinitely when no one is using it.
 * 
 * Features:
 * - Automatic voice channel disconnection after inactivity
 * - Configurable inactivity timeout
 * - Timer management per guild
 * - Graceful cleanup and messaging
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// Inactivity management system - equivalent to music_state/inactivity.py
class InactivityManager {
    /**
     * Constructor - Initialize the inactivity manager
     * 
     * Sets up the timer storage for tracking inactivity timers per guild.
     */
    constructor() {
        this.timers = new Map(); // guildId -> timeout
    }

    /**
     * Leave After Delay
     * 
     * Waits for the specified delay and then disconnects from the voice channel
     * if the bot is still connected. Sends a message to notify users.
     * 
     * @param {Object} guild - Discord guild object
     * @param {Object} channel - Discord text channel for messaging
     * @param {number} delay - Delay in milliseconds (default: 3 minutes)
     */
    async leaveAfterDelay(guild, channel, delay = 180000) { // 3 minutes default
        await new Promise(resolve => setTimeout(resolve, delay));
        
        if (guild.voiceAdapterCreator) { // Bot is still in voice
            await channel.send('No activity detected. Leaving the voice channel due to inactivity.');
            const { getVoiceConnection } = require('@discordjs/voice');
            const connection = getVoiceConnection(guild.id);
            if (connection) {
                connection.destroy();
            }
        }
    }

    /**
     * Start Timer
     * 
     * Starts an inactivity timer for a guild. If a timer already exists,
     * it will be cancelled and replaced with a new one.
     * 
     * @param {Object} guild - Discord guild object
     * @param {Object} channel - Discord text channel for messaging
     * @param {number} delay - Delay in milliseconds (default: 3 minutes)
     */
    startTimer(guild, channel, delay = 180000) {
        const guildId = guild.id;
        
        // Cancel existing timer if any
        this.cancelTimer(guildId);
        
        // Start new timer
        const timer = setTimeout(async () => {
            await this.leaveAfterDelay(guild, channel, delay);
            this.timers.delete(guildId);
        }, delay);
        
        this.timers.set(guildId, timer);
    }

    /**
     * Cancel Timer
     * 
     * Cancels the inactivity timer for a specific guild.
     * 
     * @param {string} guildId - Guild ID to cancel timer for
     */
    cancelTimer(guildId) {
        const timer = this.timers.get(guildId);
        if (timer) {
            clearTimeout(timer);
            this.timers.delete(guildId);
        }
    }

    /**
     * Has Timer
     * 
     * Checks if there's an active timer for a guild.
     * 
     * @param {string} guildId - Guild ID to check
     * @returns {boolean} True if timer exists, false otherwise
     */
    hasTimer(guildId) {
        return this.timers.has(guildId);
    }
}

// Export as default like Python module
const inactivity_timers = new InactivityManager();
module.exports = { inactivity_timers };
