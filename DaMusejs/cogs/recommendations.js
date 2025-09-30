/**
 * Recommendations Command - Personalized Music Recommendations
 * 
 * This command provides personalized music recommendations based on the user's
 * listening history and preferences. It uses the recommendation engine to
 * suggest songs that match the user's music taste.
 * 
 * Features:
 * - Personalized music recommendations
 * - Configurable recommendation count (1-10)
 * - Based on user listening history
 * - Integrates with recommendation engine
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
// Import recommendation engine for personalized suggestions
const recommendationEngine = require('../utils/recommendationEngine');

/**
 * Recommendations Command Class
 * 
 * Handles the /recommendations slash command which provides personalized
 * music recommendations based on user preferences and listening history.
 */
class RecommendationsCommand extends BaseCommand {
    /**
     * Constructor - Initialize the recommendations command
     * 
     * Sets up the slash command with name, description, and an optional
     * integer parameter for the number of recommendations to return.
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('recommendations')                        // Command name (used as /recommendations)
                .setDescription('Get personalized music recommendations')
                .addIntegerOption(option =>                        // Add optional integer option
                    option.setName('count')                        // Option name
                        .setDescription('Number of recommendations (1-10)') // Option description
                        .setMinValue(1)                           // Minimum value
                        .setMaxValue(10)                          // Maximum value
                        .setRequired(false))                      // Make option optional
        );
    }

    /**
     * Input Validation
     * 
     * Extracts the count parameter with a default value of 5.
     * No additional validation is needed as the parameter is optional.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing the recommendation count
     */
    async validateInput(interaction) {
        // Extract count parameter with default value of 5
        return { count: interaction.options.getInteger('count') || 5 };
    }

    /**
     * Command Execution
     * 
     * Retrieves personalized music recommendations by:
     * 1. Getting user and guild IDs
     * 2. Calling the recommendation engine
     * 3. Handling cases where no recommendations are available
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing recommendations or error message
     * @throws {Error} If recommendation retrieval fails
     */
    async executeCommand(interaction) {
        const { count } = await this.validateInput(interaction);

        try {
            // Get personalized recommendations from the recommendation engine
            // This analyzes user's listening history and preferences
            const recommendations = await recommendationEngine.getRecommendations(
                interaction.user.id,        // User ID for personalization
                interaction.guild.id,       // Guild ID for context
                count                       // Number of recommendations requested
            );

            // Handle case where no recommendations are available
            if (recommendations.length === 0) {
                return { message: 'No recommendations available. Try playing some songs first!' };
            }

            return { recommendations };
        } catch (error) {
            console.error('Error getting recommendations:', error);
            throw createValidationError('Failed to get recommendations. Please try again.');
        }
    }

    /**
     * Send Response
     * 
     * Sends a response with music recommendations. If no recommendations
     * are available, sends a simple message. Otherwise, creates an embed
     * showing the personalized recommendations.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing recommendations
     */
    async sendResponse(interaction, result) {
        // Handle case where no recommendations are available
        if (result.message) {
            await interaction.reply(result.message);
            return;
        }

        // Create embed for recommendations display
        const embed = new EmbedBuilder()
            .setTitle('🎵 Your Music Recommendations')    // Embed title
            .setColor(0x00ff00);                          // Green color for success

        // Build description with numbered list of recommendations
        let description = '';
        result.recommendations.forEach((song, index) => {
            description += `${index + 1}. **${song.title}** by ${song.artist}\n`;
        });

        // Set description and send the embed
        embed.setDescription(description);
        await interaction.reply({ embeds: [embed] });
    }
}

module.exports = new RecommendationsCommand();
