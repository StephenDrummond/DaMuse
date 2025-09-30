/**
 * Dislike Command - Music Interaction System
 * 
 * This command allows users to dislike the currently playing song.
 * It records the interaction in the database and updates user preferences
 * to improve the recommendation system by avoiding similar songs.
 * 
 * Features:
 * - Validates that a song is currently playing
 * - Records dislike interaction in database
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
 * Dislike Command Class
 * 
 * Handles the /dislike slash command which allows users to dislike
 * the currently playing song and improve the recommendation system.
 */
class DislikeCommand extends BaseCommand {
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('dislike')
                .setDescription('Dislike the currently playing song')
        );
    }

    async validateInput(interaction) {
        // Check if there's a currently playing song
        const { queues } = require('../music_state/queues');
        const guildId = interaction.guild.id;
        const currentSong = queues.getCurrentSong(guildId);
        
        if (!currentSong) {
            throw createValidationError('No song is currently playing to dislike!');
        }

        return { currentSong };
    }

    async executeCommand(interaction) {
        const { currentSong } = await this.validateInput(interaction);

        try {
            // Find or create the song in the database
            const song = await Song.findOrCreate({
                title: currentSong.title,
                artist: currentSong.author || 'Unknown Artist',
                url: currentSong.url,
                thumbnail: currentSong.thumbnail,
                duration: currentSong.duration || 0,
                genre: 'Unknown',
                mood: 'Neutral',
                energy: 5
            });

            // Record the dislike interaction
            await song.recordInteraction('dislike');
            
            // Update user preferences
            const userPref = await UserPreference.findOrCreate(
                interaction.user.id, 
                interaction.guild.id
            );
            await userPref.recordInteraction(song, 'dislike');

            // Record the interaction
            await MusicInteraction.recordInteraction({
                userId: interaction.user.id,
                guildId: interaction.guild.id,
                songId: song._id,
                interactionType: 'dislike'
            });

            return { 
                message: `👎 You disliked **${song.title}** by ${song.artist}.`,
                song: song
            };

        } catch (error) {
            console.error('Error in dislike command:', error);
            throw createValidationError('Failed to dislike the song. Please try again.');
        }
    }

    async sendResponse(interaction, result) {
        const embed = new EmbedBuilder()
            .setTitle('👎 Song Disliked')
            .setDescription(result.message)
            .setColor(0xff0000)
            .setThumbnail(result.song.thumbnail);

        await interaction.reply({ 
            embeds: [embed],
            flags: 64 
        });
    }
}

module.exports = new DislikeCommand();
