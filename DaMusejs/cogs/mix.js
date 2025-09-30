/**
 * Mix Command - Collaborative Music Mixing System
 * 
 * This command creates collaborative music mixes based on the preferences
 * of all users currently in the voice channel. It analyzes listening history
 * and creates personalized playlists that blend everyone's music tastes.
 * 
 * Features:
 * - Creates collaborative mixes for all voice channel users
 * - Multiple mix modes (balanced, popular, diverse)
 * - Configurable song count (5-20 songs)
 * - Integrates with music queue system
 * - Uses advanced recommendation algorithms
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
// Import music queue system for managing song queues
const { queues } = require('../music_state/queues');
// Import mix engine for creating collaborative mixes
const mixEngine = require('../utils/mixEngine');

/**
 * Mix Command Class
 * 
 * Handles the /mix slash command which creates collaborative music mixes
 * based on all users currently in the voice channel.
 */
class MixCommand extends BaseCommand {
    /**
     * Constructor - Initialize the mix command
     * 
     * Sets up the slash command with name, description, and optional parameters:
     * - count: Number of songs to add to the mix (5-20, default: 10)
     * - mode: Mix algorithm mode (balanced, popular, diverse, default: balanced)
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('mix')                                    // Command name (used as /mix)
                .setDescription('Create a collaborative mix based on all users in the voice channel')
                .addIntegerOption(option =>                        // Add optional integer option
                    option.setName('count')                        // Option name
                        .setDescription('Number of songs to add to mix (5-20)') // Option description
                        .setMinValue(5)                           // Minimum value
                        .setMaxValue(20)                          // Maximum value
                        .setRequired(false))                      // Make option optional
                .addStringOption(option =>                         // Add optional string option
                    option.setName('mode')                         // Option name
                        .setDescription('Mix mode')                // Option description
                        .setRequired(false)                        // Make option optional
                        .addChoices(                              // Add predefined choices
                            { name: 'Balanced', value: 'balanced' },   // Balanced mix mode
                            { name: 'Popular', value: 'popular' },     // Popular mix mode
                            { name: 'Diverse', value: 'diverse' }      // Diverse mix mode
                        ))
        );
    }

    /**
     * Input Validation
     * 
     * Validates that the user is in a voice channel (required for collaborative mixing)
     * and extracts the optional parameters with default values.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing count and mode parameters
     * @throws {Error} If user is not in a voice channel
     */
    async validateInput(interaction) {
        // Ensure user is in a voice channel (required for collaborative mixing)
        if (!isInVoiceChannel(interaction.member)) {
            throw createValidationError('You must be in a voice channel to create a mix!');
        }

        // Extract optional parameters with default values
        const count = interaction.options.getInteger('count') || 10;  // Default to 10 songs
        const mode = interaction.options.getString('mode') || 'balanced'; // Default to balanced mode

        return { count, mode };
    }

    /**
     * Command Execution
     * 
     * Creates a collaborative mix by:
     * 1. Getting all users in the voice channel
     * 2. Analyzing their music preferences
     * 3. Creating a personalized mix
     * 4. Adding songs to the music queue
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing mix results and metadata
     * @throws {Error} If mix creation fails or no users found
     */
    async executeCommand(interaction) {
        const { count, mode } = await this.validateInput(interaction);

        try {
            // Get all users in the voice channel (excluding bots)
            const voiceChannel = interaction.member.voice.channel;
            const usersInChannel = voiceChannel.members.filter(member => !member.user.bot);
            
            // Ensure there are other users in the channel for collaboration
            if (usersInChannel.size === 0) {
                throw createValidationError('No other users found in the voice channel!');
            }

            // Extract user IDs for mix engine
            const userIds = Array.from(usersInChannel.keys());
            
            // Create collaborative mix using the mix engine
            // This analyzes all users' preferences and creates a balanced playlist
            const mixSongs = await mixEngine.createCollaborativeMix(
                userIds,                    // Array of user IDs in the channel
                interaction.guild.id,       // Guild ID for context
                count,                      // Number of songs requested
                mode                        // Mix algorithm mode
            );

            // Handle case where no mix can be created (insufficient data)
            if (mixSongs.length === 0) {
                return { 
                    message: 'No mix available. Users need to have some music history first!' 
                };
            }

            // Add all mix songs to the music queue
            const guildId = interaction.guild.id;
            for (const song of mixSongs) {
                queues.addToQueue(guildId, {
                    title: song.title,          // Song title
                    url: song.url,             // Song URL (YouTube, Spotify, etc.)
                    thumbnail: song.thumbnail,  // Song thumbnail image
                    duration: song.duration,   // Song duration in milliseconds
                    author: song.artist        // Artist name
                });
            }

            return { 
                mixSongs,                      // Array of songs added to mix
                userCount: usersInChannel.size, // Number of users in collaboration
                mode                           // Mix mode used
            };

        } catch (error) {
            console.error('Error creating mix:', error);
            throw createValidationError('Failed to create mix. Please try again.');
        }
    }

    /**
     * Send Response
     * 
     * Sends a response with mix creation results. If no mix was created,
     * sends a simple message. Otherwise, creates an embed showing the
     * mix details and song list.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing mix data
     */
    async sendResponse(interaction, result) {
        // Handle case where no mix could be created
        if (result.message) {
            await interaction.reply(result.message);
            return;
        }

        // Create embed for successful mix creation
        const embed = new EmbedBuilder()
            .setTitle('🎵 Collaborative Mix Created!')
            .setDescription(`Created a **${result.mode}** mix for ${result.userCount} users`)
            .setColor(0x00ff00); // Green color for success

        // Build song list description (show first 10 songs)
        let description = `Added ${result.mixSongs.length} songs to the queue:\n\n`;
        result.mixSongs.slice(0, 10).forEach((song, index) => {
            description += `${index + 1}. **${song.title}** by ${song.artist}\n`;
        });

        // Add indicator if there are more songs than displayed
        if (result.mixSongs.length > 10) {
            description += `\n... and ${result.mixSongs.length - 10} more songs!`;
        }

        embed.setDescription(description);
        await interaction.reply({ embeds: [embed] });
    }
}

module.exports = new MixCommand();
