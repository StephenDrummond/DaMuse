/**
 * Autoplay Command - Music Recommendation System
 * 
 * This command enables or disables autoplay functionality which provides
 * personalized music recommendations based on user preferences and listening history.
 * 
 * Features:
 * - Enable/disable autoplay with user choice
 * - Validates user is in voice channel
 * - Updates user preferences in database
 * - Integrates with recommendation engine
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// ⚠️  TEMPORARY: Using in-memory database models for testing
// Import Discord.js components for slash command creation
const { SlashCommandBuilder } = require('discord.js');
// Import the base command class that provides common functionality
const { BaseCommand } = require('../utils/commandTemplate');
// Import error handling utilities for validation errors
const { createValidationError } = require('../utils/errorHandler');
// Import helper functions for command validation
const { isInVoiceChannel } = require('../utils/commandHelpers');
// Import autoplay manager for handling recommendation logic
const autoplayManager = require('../utils/autoplayManager');
// Import temporary database models (will be replaced with MongoDB models)
const UserPreference = require('../models/tempUserPreference');

/**
 * Autoplay Command Class
 * 
 * Handles the /autoplay slash command which allows users to enable
 * or disable personalized music recommendations.
 */
class AutoplayCommand extends BaseCommand {
    /**
     * Constructor - Initialize the autoplay command
     * 
     * Sets up the slash command with name, description, and a required
     * string option for enabling or disabling autoplay.
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('autoplay')                           // Command name (used as /autoplay)
                .setDescription('Enable or disable autoplay for personalized music recommendations')
                .addStringOption(option =>                     // Add required string option
                    option.setName('action')                  // Option name
                        .setDescription('Enable or disable autoplay') // Option description
                        .setRequired(true)                    // Make option required
                        .addChoices(                          // Add predefined choices
                            { name: 'Enable', value: 'enable' },   // Enable choice
                            { name: 'Disable', value: 'disable' } // Disable choice
                        ))
        );
    }

    /**
     * Input Validation
     * 
     * Validates that the user is in a voice channel (required for autoplay)
     * and extracts the action choice from the interaction.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing the action choice
     * @throws {Error} If user is not in a voice channel
     */
    async validateInput(interaction) {
        // Ensure user is in a voice channel (required for autoplay functionality)
        if (!isInVoiceChannel(interaction.member)) {
            throw createValidationError('You must be in a voice channel to use autoplay!');
        }

        // Extract the action choice from the interaction
        const action = interaction.options.getString('action');
        return { action };
    }

    /**
     * Command Execution
     * 
     * Processes the autoplay enable/disable request by:
     * 1. Updating the autoplay manager state
     * 2. Saving user preferences to the database
     * 3. Providing appropriate feedback to the user
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing success message
     */
    async executeCommand(interaction) {
        const { action } = await this.validateInput(interaction);

        const guildId = interaction.guild.id;
        const userId = interaction.user.id;

        if (action === 'enable') {
            // Enable autoplay in the manager
            autoplayManager.enableAutoplay(guildId, userId);
            
            // Update user preferences in the database
            const userPref = await UserPreference.findOrCreate(userId, guildId);
            userPref.autoplayEnabled = true;
            await userPref.save();

            return { message: '🎵 Autoplay enabled! I\'ll recommend songs based on your music taste.' };
        } else {
            // Disable autoplay in the manager
            autoplayManager.disableAutoplay(guildId);
            
            // Update user preferences in the database
            const userPref = await UserPreference.findOrCreate(userId, guildId);
            userPref.autoplayEnabled = false;
            await userPref.save();

            return { message: '⏹️ Autoplay disabled.' };
        }
    }

    /**
     * Send Response
     * 
     * Sends a confirmation message about the autoplay status change.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing the message
     */
    async sendResponse(interaction, result) {
        await interaction.reply(result.message);
    }
}

module.exports = new AutoplayCommand();
