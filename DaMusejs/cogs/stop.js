/**
 * Stop Command - Music Control
 * 
 * This command stops all music playback and clears the queue.
 * It also disconnects the bot from the voice channel and cancels
 * any inactivity timers.
 * 
 * Features:
 * - Stops current playback
 * - Clears the entire queue
 * - Disconnects from voice channel
 * - Cancels inactivity timers
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// Import Discord.js components for slash command creation
const { SlashCommandBuilder } = require('discord.js');
// Import the base command class that provides common functionality
const { BaseCommand } = require('../utils/commandTemplate');
// Import error handling utilities for validation errors
const { createValidationError } = require('../utils/errorHandler');
// Import Discord.js voice utilities for voice connection management
const { getVoiceConnection } = require('@discordjs/voice');
// Import the music queue system to access player and queue state
const { queues } = require('../music_state/queues');
// Import inactivity timer system for cleanup
const { inactivity_timers } = require('../music_state/inactivity');

/**
 * Stop Command Class
 * 
 * Handles the /stop slash command which completely stops
 * music playback and clears all queues.
 */
class StopCommand extends BaseCommand {
    /**
     * Constructor - Initialize the stop command
     * 
     * Sets up the slash command with name and description.
     * No additional options are required for this command.
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('stop')                               // Command name (used as /stop)
                .setDescription('Stop playing and clear the queue') // Command description
        );
    }

    /**
     * Input Validation
     * 
     * No validation is needed for the stop command as it doesn't
     * require any user input or specific conditions.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Empty object (no validation needed)
     */
    async validateInput(interaction) {
        return {};
    }

    /**
     * Command Execution
     * 
     * Completely stops music playback by:
     * 1. Stopping the audio player
     * 2. Clearing the entire queue
     * 3. Disconnecting from voice channel
     * 4. Canceling inactivity timers
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing success message
     * @throws {Error} If nothing is playing or no connection exists
     */
    async executeCommand(interaction) {
        const guildId = interaction.guild.id;
        const connection = getVoiceConnection(guildId);
        const player = queues.getPlayer(guildId);

        // Validate that there's an active connection and player
        if (!connection || !player) {
            throw createValidationError('Nothing is playing.');
        }

        // Stop the audio player and clear all queue data
        player.stop();                    // Stop current playback
        queues.clearQueue(guildId);       // Clear the entire queue
        queues.setPlaying(guildId, false); // Mark as not playing

        // Disconnect from the voice channel completely
        connection.destroy();

        // Cancel any inactivity timer to prevent auto-disconnect
        inactivity_timers.cancelTimer(guildId);

        return { message: 'Stopped playback and cleared queue.' };
    }

    /**
     * Send Response
     * 
     * Sends a confirmation message that playback was stopped.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing the message
     */
    async sendResponse(interaction, result) {
        await interaction.reply(result.message);
    }
}

module.exports = new StopCommand();
