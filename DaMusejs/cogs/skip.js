/**
 * Skip Command - Music Control
 * 
 * This command allows users to skip the currently playing song.
 * It stops the current audio and moves to the next song in the queue.
 * 
 * Features:
 * - Skips current song
 * - Validates that music is playing
 * - Moves to next song in queue automatically
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

/**
 * Skip Command Class
 * 
 * Handles the /skip slash command which skips the currently
 * playing song and moves to the next song in the queue.
 */
class SkipCommand extends BaseCommand {
    /**
     * Constructor - Initialize the skip command
     * 
     * Sets up the slash command with name and description.
     * No additional options are required for this command.
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('skip')                           // Command name (used as /skip)
                .setDescription('Skip the current song')    // Command description
        );
    }

    /**
     * Input Validation
     * 
     * No validation is needed for the skip command as it doesn't
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
     * Skips the currently playing song by stopping the audio player.
     * The queue system will automatically start the next song.
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
            throw createValidationError('Nothing is playing to skip.');
        }

        // Check if the player is actually playing a song
        if (player.state.status === 'playing') {
            // Stop the current song (this will trigger the next song to play)
            player.stop();
            return { message: 'Skipped current song.' };
        } else {
            throw createValidationError('Nothing is playing to skip.');
        }
    }

    /**
     * Send Response
     * 
     * Sends a confirmation message that the song was skipped.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing the message
     */
    async sendResponse(interaction, result) {
        await interaction.reply(result.message);
    }
}

module.exports = new SkipCommand();
