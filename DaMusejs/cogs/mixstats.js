/**
 * Mix Stats Command - Music Statistics Display
 * 
 * This command displays music statistics for all users currently in the voice channel.
 * It shows collaborative music data including active users, total songs played,
 * common genres, and top artists based on the group's listening history.
 * 
 * Features:
 * - Shows voice channel music statistics
 * - Displays active users and total songs played
 * - Lists top genres and artists
 * - Provides collaborative music insights
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// ⚠️  TEMPORARY: Using in-memory database models for testing
// Import Discord.js components for slash command and embed creation
const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
// Import the base command class that provides common functionality
const { BaseCommand } = require('../utils/commandTemplate');
// Import error handling utilities for validation errors
const { createValidationError } = require('../utils/errorHandler');
// Import helper functions for command validation
const { isInVoiceChannel } = require('../utils/commandHelpers');
// Import mix engine for accessing music statistics
const mixEngine = require('../utils/mixEngine');

/**
 * Mix Stats Command Class
 * 
 * Handles the /mixstats slash command which displays music statistics
 * for all users currently in the voice channel.
 */
class MixStatsCommand extends BaseCommand {
    /**
     * Constructor - Initialize the mix stats command
     * 
     * Sets up the slash command with name and description.
     * No additional options are required for this command.
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('mixstats')                                    // Command name (used as /mixstats)
                .setDescription('Show music statistics for all users in the voice channel')
        );
    }

    /**
     * Input Validation
     * 
     * Validates that the user is in a voice channel (required for viewing
     * collaborative music statistics).
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Empty object (no additional validation needed)
     * @throws {Error} If user is not in a voice channel
     */
    async validateInput(interaction) {
        // Ensure user is in a voice channel (required for collaborative stats)
        if (!isInVoiceChannel(interaction.member)) {
            throw createValidationError('You must be in a voice channel to view mix stats!');
        }

        return {};
    }

    /**
     * Command Execution
     * 
     * Retrieves music statistics for all users in the voice channel by:
     * 1. Getting all users in the voice channel
     * 2. Collecting their user IDs
     * 3. Fetching collaborative music statistics
     * 4. Returning formatted statistics data
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing statistics and user count
     * @throws {Error} If no users found or statistics retrieval fails
     */
    async executeCommand(interaction) {
        const { } = await this.validateInput(interaction);

        try {
            // Get all users in the voice channel (excluding bots)
            const voiceChannel = interaction.member.voice.channel;
            const usersInChannel = voiceChannel.members.filter(member => !member.user.bot);
            
            // Ensure there are other users in the channel for statistics
            if (usersInChannel.size === 0) {
                throw createValidationError('No other users found in the voice channel!');
            }

            // Extract user IDs for statistics analysis
            const userIds = Array.from(usersInChannel.keys());
            
            // Get collaborative music statistics from mix engine
            // This analyzes all users' music preferences and listening history
            const stats = await mixEngine.getMixStats(userIds, interaction.guild.id);

            return { 
                stats,                      // Statistics data (genres, artists, etc.)
                userCount: usersInChannel.size // Number of users in collaboration
            };

        } catch (error) {
            console.error('Error getting mix stats:', error);
            throw createValidationError('Failed to get mix statistics. Please try again.');
        }
    }

    /**
     * Send Response
     * 
     * Creates and sends an embed response showing music statistics for
     * all users in the voice channel, including active users, total songs,
     * top genres, and top artists.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing statistics data
     */
    async sendResponse(interaction, result) {
        const { stats, userCount } = result;

        // Create embed with statistics title and basic info
        const embed = new EmbedBuilder()
            .setTitle('🎵 Voice Channel Music Statistics')
            .setDescription(`Music stats for ${userCount} users in the voice channel`)
            .setColor(0x00ff00); // Green color for the embed

        // Build description with user activity and song statistics
        let description = `**Active Users:** ${stats.activeUsers}/${stats.totalUsers}\n`;
        description += `**Total Songs Played:** ${stats.totalSongsPlayed}\n\n`;

        // Add top genres section if data is available
        if (stats.commonGenres.length > 0) {
            description += `**Top Genres:**\n`;
            stats.commonGenres.slice(0, 3).forEach((genre, index) => {
                description += `${index + 1}. ${genre.genre} (${genre.count} likes)\n`;
            });
            description += '\n';
        }

        // Add top artists section if data is available
        if (stats.commonArtists.length > 0) {
            description += `**Top Artists:**\n`;
            stats.commonArtists.slice(0, 3).forEach((artist, index) => {
                description += `${index + 1}. ${artist.artist} (${artist.count} likes)\n`;
            });
        }

        // Set the description and send the embed
        embed.setDescription(description);
        await interaction.reply({ embeds: [embed] });
    }
}

module.exports = new MixStatsCommand();
