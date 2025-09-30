/**
 * Like Command - Music Interaction System
 * 
 * This command allows users to like the currently playing song.
 * It records the interaction in the database and updates user preferences
 * for better music recommendations.
 * 
 * Features:
 * - Validates that a song is currently playing
 * - Records like interaction in database
 * - Updates user preferences
 * - Tracks music interaction history
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
// Import temporary database models (will be replaced with MongoDB models)
const Song = require('../models/tempSong');
const UserPreference = require('../models/tempUserPreference');
const MusicInteraction = require('../models/tempMusicInteraction');

/**
 * Like Command Class
 * 
 * Handles the /like slash command which allows users to like
 * the currently playing song and improve the recommendation system.
 */
class LikeCommand extends BaseCommand {
    /**
     * Constructor - Initialize the like command
     * 
     * Sets up the slash command with name and description.
     * No additional options are required for this command.
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('like')                           // Command name (used as /like)
                .setDescription('Like the currently playing song') // Command description
        );
    }

    /**
     * Input Validation
     * 
     * Validates that there is a currently playing song that can be liked.
     * This prevents users from trying to like when no music is playing.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing the current song information
     * @throws {Error} If no song is currently playing
     */
    async validateInput(interaction) {
        // Import the music queue system to check for currently playing songs
        const { queues } = require('../music_state/queues');
        const guildId = interaction.guild.id;
        const currentSong = queues.getCurrentSong(guildId);
        
        // Ensure there's a song currently playing
        if (!currentSong) {
            throw createValidationError('No song is currently playing to like!');
        }

        return { currentSong };
    }

    /**
     * Command Execution
     * 
     * Processes the like interaction by:
     * 1. Finding or creating the song in the database
     * 2. Recording the like interaction on the song
     * 3. Updating user preferences for better recommendations
     * 4. Logging the interaction for analytics
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing success message and song data
     * @throws {Error} If database operations fail
     */
    async executeCommand(interaction) {
        const { currentSong } = await this.validateInput(interaction);

        try {
            // Find or create the song in the database with metadata
            const song = await Song.findOrCreate({
                title: currentSong.title,                    // Song title
                artist: currentSong.author || 'Unknown Artist', // Artist name (fallback if unknown)
                url: currentSong.url,                        // YouTube/stream URL
                thumbnail: currentSong.thumbnail,            // Song thumbnail image
                duration: currentSong.duration || 0,        // Song duration in milliseconds
                genre: 'Unknown',                           // Genre (could be enhanced with detection)
                mood: 'Neutral',                           // Mood classification
                energy: 5                                  // Energy level (1-10 scale)
            });

            // Record the like interaction on the song object
            // This updates the song's like count and recommendation score
            await song.recordInteraction('like');
            
            // Update user preferences to improve future recommendations
            const userPref = await UserPreference.findOrCreate(
                interaction.user.id,  // Discord user ID
                interaction.guild.id  // Discord guild (server) ID
            );
            await userPref.recordInteraction(song, 'like');

            // Record the interaction in the interaction history
            // This is used for analytics and recommendation algorithms
            await MusicInteraction.recordInteraction({
                userId: interaction.user.id,        // User who performed the action
                guildId: interaction.guild.id,       // Server where action occurred
                songId: song._id,                    // Database ID of the song
                interactionType: 'like'             // Type of interaction performed
            });

            return { 
                message: `👍 You liked **${song.title}** by ${song.artist}!`,
                song: song
            };

        } catch (error) {
            console.error('Error in like command:', error);
            throw createValidationError('Failed to like the song. Please try again.');
        }
    }

    /**
     * Send Response
     * 
     * Creates and sends an embed response confirming the like action.
     * The response is private (only visible to the user who used the command).
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing message and song data
     */
    async sendResponse(interaction, result) {
        // Create an embed with success message and song thumbnail
        const embed = new EmbedBuilder()
            .setTitle('👍 Song Liked!')                    // Embed title
            .setDescription(result.message)                // Success message with song details
            .setColor(0x00ff00)                           // Green color for success
            .setThumbnail(result.song.thumbnail);        // Song thumbnail image

        // Send the response as a private message (only visible to the user)
        await interaction.reply({ 
            embeds: [embed],
            flags: 64  // Only the user who used the command can see this response
        });
    }
}

module.exports = new LikeCommand();
