/**
 * Command Deployment Script
 * 
 * This script registers all slash commands and context menu commands
 * with Discord's API. It must be run whenever commands are added,
 * modified, or removed to keep Discord in sync.
 * 
 * Usage: node deploy-commands.js
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// Import Discord.js REST API for command registration
const { REST, Routes } = require('discord.js');
// Import Node.js path utilities for file system operations
const { join } = require('node:path');
// Import Node.js file system utilities for reading directories
const { readdirSync } = require('node:fs');
// Load environment variables from .env file
require('dotenv').config();

// Array to store all commands that will be registered with Discord
const commands = [];

/**
 * Load Slash Commands
 * 
 * This section loads all slash command files from the 'cogs' directory
 * and prepares them for registration with Discord's API.
 */

// Define the path to the cogs directory containing all command files
const cogsPath = join(__dirname, 'cogs');
// Read all JavaScript files from the cogs directory
const commandFiles = readdirSync(cogsPath).filter(file => file.endsWith('.js'));

// Iterate through each command file and prepare it for deployment
for (const file of commandFiles) {
    const filePath = join(cogsPath, file);
    const command = require(filePath);
    
    // Validate that the command has the required properties
    if (command.data && command.execute) {
        // Convert command data to JSON format for Discord API
        commands.push(command.data.toJSON());
        console.log(`[INFO] Loaded command: ${command.data.name}`);
    } else {
        // Log a warning for invalid command files
        console.warn(`[WARNING] Command ${file} is missing required "data" or "execute" property`);
    }
}

/**
 * Load Context Menu Commands
 * 
 * This section loads context menu commands (right-click menu options)
 * from the contextMenus directory.
 */

// Define the path to the contextMenus directory containing context menu files
const contextMenusPath = join(__dirname, 'contextMenus');
// Read all JavaScript files from the contextMenus directory
const contextMenuFiles = readdirSync(contextMenusPath).filter(file => file.endsWith('.js'));

// Iterate through context menu files and prepare them for deployment
for (const file of contextMenuFiles) {
    const filePath = join(contextMenusPath, file);
    const contextMenu = require(filePath);
    
    // Validate that the context menu has the required properties
    if (contextMenu.data && contextMenu.data.toJSON && contextMenu.execute) {
        // Convert context menu data to JSON format for Discord API
        commands.push(contextMenu.data.toJSON());
        console.log(`[INFO] Loaded context menu: ${contextMenu.data.name}`);
    }
}

/**
 * Command Deployment Process
 * 
 * This section handles the actual registration of commands with Discord's API.
 * It uses the REST API to register all commands globally.
 */

// Initialize the REST API client with the bot token
const rest = new REST().setToken(process.env.DISCORD_TOKEN);

// Deploy commands to Discord using an immediately invoked async function
(async () => {
    try {
        console.log(`Started refreshing ${commands.length} application (/) commands.`);

        // Register all commands with Discord's API
        // The put method completely replaces all existing commands with the new set
        const data = await rest.put(
            Routes.applicationCommands(process.env.CLIENT_ID), // Global command registration
            { body: commands }, // Send all commands in the request body
        );

        console.log(`Successfully reloaded ${data.length} application (/) commands.`);
    } catch (error) {
        console.error(error);
    }
})();
