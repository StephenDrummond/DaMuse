/**
 * Base Command Template - Command Architecture
 * 
 * This file provides the base class for all Discord slash commands.
 * It implements a standardized command structure with validation,
 * execution, and response handling.
 * 
 * Features:
 * - Standardized command lifecycle
 * - Built-in error handling
 * - Deferred reply support
 * - Ephemeral response support
 * - Input validation framework
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// Import Discord.js components for slash command creation
const { SlashCommandBuilder } = require('discord.js');

/**
 * Base Command Class
 * 
 * Abstract base class that provides the common structure and functionality
 * for all Discord slash commands. Subclasses must implement the abstract methods.
 */
class BaseCommand {
    /**
     * Constructor - Initialize the base command
     * 
     * @param {SlashCommandBuilder} commandBuilder - The Discord.js command builder instance
     */
    constructor(commandBuilder) {
        this.data = commandBuilder;
    }

    /**
     * Should Defer Reply
     * 
     * Determines if the command should defer its reply (for long-running operations).
     * Override in subclasses to return true for commands that take time to execute.
     * 
     * @returns {boolean} True if reply should be deferred, false otherwise
     */
    shouldDeferReply() {
        return false;
    }

    /**
     * Is Private
     * 
     * Determines if the command response should be private (only visible to the user).
     * Override in subclasses to return true for private responses.
     * 
     * @returns {boolean} True if response should be private, false otherwise
     */
    isEphemeral() {
        return false;
    }

    /**
     * Validate Input
     * 
     * Validates the command input and user permissions.
     * Override in subclasses to implement specific validation logic.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Validation result object
     */
    async validateInput(interaction) {
        // Override in subclasses
        return {};
    }

    /**
     * Execute Command
     * 
     * Performs the main command logic.
     * Must be implemented in subclasses.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Command result object
     * @throws {Error} If not implemented in subclass
     */
    async executeCommand(interaction) {
        // Override in subclasses
        throw new Error('executeCommand must be implemented');
    }

    /**
     * Send Response
     * 
     * Sends the response to the user.
     * Override in subclasses to customize response format.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand
     */
    async sendResponse(interaction, result) {
        // Override in subclasses
        await interaction.reply('Command executed successfully!');
    }

    /**
     * Execute - Main Command Entry Point
     * 
     * This is the main method that orchestrates the command execution flow:
     * 1. Defer reply if needed (for long-running operations)
     * 2. Validate input and permissions
     * 3. Execute the command logic
     * 4. Send the response
     * 5. Handle any errors gracefully
     * 
     * @param {Object} interaction - Discord interaction object
     */
    async execute(interaction) {
        try {
            // Check if interaction is still valid (not expired)
            if (interaction.isExpired && interaction.isExpired()) {
                console.warn(`Interaction expired for command ${this.data.name}`);
                return;
            }

            // Defer reply if the command takes time to execute
            if (this.shouldDeferReply()) {
                const options = {};
                if (this.isEphemeral()) {
                    options.flags = 64; // Use flags instead of deprecated ephemeral
                }
                await interaction.deferReply(options);
            }

            // Validate input and permissions
            const validation = await this.validateInput(interaction);
            if (!validation) return;

            // Execute the main command logic
            const result = await this.executeCommand(interaction);
            
            // Send the response to the user
            await this.sendResponse(interaction, result);
        } catch (error) {
            // Log the error for debugging
            console.error(`Error in command ${this.data.name}:`, error);
            
            // Check if it's an interaction timeout or acknowledgment error
            if (error.code === 10062 || error.code === 40060 || 
                error.message.includes('Unknown interaction') || 
                error.message.includes('Interaction has already been acknowledged') ||
                error.message.includes('already been acknowledged')) {
                console.warn(`Interaction expired or already acknowledged for command ${this.data.name}`);
                return; // Don't try to respond to expired/acknowledged interactions
            }
            
            // Send error message to user based on interaction state
            try {
                if (interaction.deferred && !interaction.replied) {
                    // If we deferred but haven't replied yet, edit the deferred reply
                    await interaction.editReply({ 
                        content: 'An error occurred while processing your request.',
                        flags: 64 // Use flags instead of deprecated ephemeral
                    });
                } else if (!interaction.replied) {
                    // If we haven't replied at all, send a new reply
                    await interaction.reply({ 
                        content: 'An error occurred while processing your request.', 
                        flags: 64 // Use flags instead of deprecated ephemeral
                    });
                }
            } catch (replyError) {
                // If we can't reply to the interaction, just log it
                console.error('Failed to send error response:', replyError.message);
            }
        }
    }
}

module.exports = { BaseCommand };

