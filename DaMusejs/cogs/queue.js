/**
 * Queue Command - Music Queue Display
 * 
 * This command displays the current music queue for the guild.
 * It shows all queued songs with their titles and durations in a formatted list.
 * 
 * Features:
 * - Displays current music queue
 * - Shows song titles and durations
 * - Formatted embed response
 * - Handles empty queue gracefully
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// Import Discord.js components for slash command and embed creation
const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
// Import the base command class that provides common functionality
const { BaseCommand } = require('../utils/commandTemplate');
// Import error handling utilities for validation errors
const { createValidationError } = require('../utils/errorHandler');
// Import the music queue system to access current queue
const { queues } = require('../music_state/queues');

/**
 * Queue Command Class
 * 
 * Handles the /queue slash command which displays the current
 * music queue for the guild with song titles and durations.
 */
class QueueCommand extends BaseCommand {
    /**
     * Constructor - Initialize the queue command
     * 
     * Sets up the slash command with name and description.
     * No additional options are required for this command.
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('queue')                           // Command name (used as /queue)
                .setDescription('Show the current music queue') // Command description
        );
    }

    /**
     * Input Validation
     * 
     * No validation is needed for the queue command as it doesn't
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
     * Retrieves the current music queue for the guild and validates
     * that it's not empty before proceeding.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing the queue data
     * @throws {Error} If the queue is empty
     */
    async executeCommand(interaction) {
        const guildId = interaction.guild.id;
        const queue = queues.getQueue(guildId);

        // Check if queue exists and has songs
        if (!queue || queue.length === 0) {
            throw createValidationError('The queue is empty.');
        }

        return { queue };
    }

    /**
     * Send Response
     * 
     * Creates and sends an embed response showing the current music queue.
     * Each song is displayed with its position, title, and duration.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing the queue data
     */
    async sendResponse(interaction, result) {
        // Create the main embed with title and color
        const embed = new EmbedBuilder()
            .setTitle('🎵 Music Queue')    // Embed title with music note emoji
            .setColor(0x00ff00);          // Green color for the embed

        // Build the description string with all queued songs
        let description = '';
        result.queue.forEach((song, index) => {
            // Convert duration from milliseconds to seconds, then to minutes:seconds format
            const duration = Math.floor(song.duration / 1000);  // Convert to seconds
            const minutes = Math.floor(duration / 60);          // Get minutes
            const seconds = duration % 60;                      // Get remaining seconds
            const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`; // Format as MM:SS
            
            // Add song to description with position, title, and duration
            description += `${index + 1}. **${song.title}** (${timeString})\n`;
        });

        // Set the description and send the embed
        embed.setDescription(description);
        await interaction.reply({ embeds: [embed] });
    }
}

module.exports = new QueueCommand();
