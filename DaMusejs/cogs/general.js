/**
 * General Commands - Hello Command
 * 
 * This file contains general utility commands for the bot.
 * Currently includes a simple hello command for testing purposes.
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

/**
 * Hello Command Class
 * 
 * A simple command that greets the user and displays guild information.
 * This is primarily used for testing bot connectivity and basic functionality.
 */
class HelloCommand extends BaseCommand {
    /**
     * Constructor - Initialize the hello command
     * 
     * Sets up the slash command with name and description.
     * No additional options are required for this simple command.
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('hello')                    // Command name (used as /hello)
                .setDescription('Say hello to the bot') // Command description shown in Discord
        );
    }

    /**
     * Input Validation
     * 
     * No validation is needed for the hello command as it doesn't
     * require any user input or specific conditions.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Empty object (no validation needed)
     */
    async validateInput(interaction) {
        // No validation needed for hello command
        return {};
    }

    /**
     * Command Execution
     * 
     * Creates a personalized greeting message that includes:
     * - User mention
     * - Guild (server) name
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing the greeting message
     */
    async executeCommand(interaction) {
        const message = `Hello ${interaction.user}! You are a member of ${interaction.guild.name}`;
        return { message };
    }

    /**
     * Send Response
     * 
     * Sends the greeting message as a reply to the user.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing the message
     */
    async sendResponse(interaction, result) {
        await interaction.reply(result.message);
    }
}

module.exports = new HelloCommand();

