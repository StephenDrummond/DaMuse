/**
 * Command Helpers - Utility Functions
 * 
 * This file contains utility functions for command validation and
 * permission checking. It provides common validation logic that
 * can be reused across multiple commands.
 * 
 * Features:
 * - Permission level checking
 * - Voice channel validation
 * - User role validation
 * - Moderation permission checks
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// Import Discord.js permission flags for role and permission checking
const { PermissionFlagsBits } = require('discord.js');

/**
 * Check Moderation Permission
 * 
 * Validates if a user has the required permission level for moderation commands.
 * Supports different permission levels: admins, moderators, and DJ roles.
 * 
 * @param {Object} interaction - Discord interaction object
 * @param {string} permissionLevel - Required permission level ('admins', 'moderators', 'dj')
 * @returns {boolean} True if user has required permissions, false otherwise
 */
async function checkModerationPermission(interaction, permissionLevel = 'moderators') {
    const member = interaction.member;
    
    // Ensure member exists
    if (!member) return false;

    // Administrators always have permission
    if (member.permissions.has(PermissionFlagsBits.Administrator)) {
        return true;
    }

    // Check for specific roles based on permission level
    switch (permissionLevel) {
        case 'admins':
            // Only administrators
            return member.permissions.has(PermissionFlagsBits.Administrator);
        case 'moderators':
            // Moderators or administrators
            return member.permissions.has(PermissionFlagsBits.ModerateMembers) || 
                   member.permissions.has(PermissionFlagsBits.Administrator);
        case 'dj':
            // DJ role, moderators, or administrators
            return member.permissions.has(PermissionFlagsBits.ModerateMembers) || 
                   member.permissions.has(PermissionFlagsBits.Administrator) ||
                   member.roles.cache.some(role => role.name.toLowerCase().includes('dj'));
        default:
            return false;
    }
}

/**
 * Is In Voice Channel
 * 
 * Checks if a user is currently in a voice channel.
 * 
 * @param {Object} member - Discord guild member object
 * @returns {boolean} True if user is in a voice channel, false otherwise
 */
function isInVoiceChannel(member) {
    return member.voice.channel !== null;
}

/**
 * Is In Same Voice Channel
 * 
 * Checks if a user and the bot are in the same voice channel.
 * This is useful for music commands that require the user to be
 * in the same channel as the bot.
 * 
 * @param {Object} member - Discord guild member object (user)
 * @param {Object} botMember - Discord guild member object (bot)
 * @returns {boolean} True if both are in the same voice channel, false otherwise
 */
function isInSameVoiceChannel(member, botMember) {
    return member.voice.channel && 
           botMember.voice.channel && 
           member.voice.channel.id === botMember.voice.channel.id;
}

module.exports = {
    checkModerationPermission,
    isInVoiceChannel,
    isInSameVoiceChannel
};

