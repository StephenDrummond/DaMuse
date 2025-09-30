/**
 * Error Handler - Custom Error Classes
 * 
 * This file defines custom error classes for the Discord bot to provide
 * better error handling and user feedback. It includes validation errors
 * and command execution errors with specific error types.
 * 
 * Features:
 * - Custom error classes with specific names
 * - Factory functions for easy error creation
 * - Better error categorization for debugging
 * - Consistent error handling across the bot
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

/**
 * Validation Error Class
 * 
 * Thrown when user input validation fails or when required conditions
 * are not met (e.g., user not in voice channel, invalid parameters).
 * These errors are typically user-facing and should provide helpful messages.
 */
class ValidationError extends Error {
    /**
     * Constructor - Create a validation error
     * 
     * @param {string} message - Error message to display to the user
     */
    constructor(message) {
        super(message);
        this.name = 'ValidationError';
    }
}

/**
 * Command Error Class
 * 
 * Thrown when command execution fails due to internal errors,
 * API failures, or other system-level issues. These errors are
 * typically logged and may show generic error messages to users.
 */
class CommandError extends Error {
    /**
     * Constructor - Create a command error
     * 
     * @param {string} message - Error message describing the failure
     */
    constructor(message) {
        super(message);
        this.name = 'CommandError';
    }
}

/**
 * Create Validation Error
 * 
 * Factory function to create a validation error with a user-friendly message.
 * 
 * @param {string} message - Error message to display to the user
 * @returns {ValidationError} New validation error instance
 */
function createValidationError(message) {
    return new ValidationError(message);
}

/**
 * Create Command Error
 * 
 * Factory function to create a command error for internal failures.
 * 
 * @param {string} message - Error message describing the failure
 * @returns {CommandError} New command error instance
 */
function createCommandError(message) {
    return new CommandError(message);
}

// Export all error classes and factory functions
module.exports = {
    ValidationError,
    CommandError,
    createValidationError,
    createCommandError
};

