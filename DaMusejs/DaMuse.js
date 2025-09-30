/**
 * DaMuse Discord Music Bot - Main Entry Point
 * 
 * This is the main file that initializes and runs the Discord music bot.
 * It handles command loading, event processing, and bot lifecycle management.
 * 
 * Features:
 * - Slash command handling
 * - Context menu support
 * - Voice channel integration
 * - Database connectivity
 * - Autoplay management
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// Import Discord.js core components for bot functionality
const { Client, GatewayIntentBits, Collection, Events } = require('discord.js');
// Import Node.js path utilities for file system operations
const { join } = require('node:path');
// Import Node.js file system utilities for reading directories
const { readdirSync } = require('node:fs');

// TEMPORARY DATABASE - FOR TESTING ONLY
// TODO: Replace with original database.js when MongoDB is set up
// This is a temporary in-memory database for testing purposes
const database = require('./utils/tempDatabaseConnection');
// Import autoplay manager for handling automatic song recommendations
const autoplayManager = require('./utils/autoplayManager');
// Import queue system for voice connection cleanup
const { queues } = require('./music_state/queues');
// Load environment variables from .env file
require('dotenv').config();

/**
 * Process Management - Prevent Multiple Instances
 * 
 * This section checks for existing DaMuse processes and prevents
 * multiple instances from running simultaneously, which can cause
 * conflicts with voice connections and database operations.
 */

// Import Node.js process utilities
const { exec } = require('child_process');
const os = require('os');

/**
 * Check for existing DaMuse processes
 * 
 * @returns {Promise<boolean>} True if other DaMuse processes are running
 */
async function checkForExistingProcesses() {
    return new Promise((resolve) => {
        if (os.platform() === 'win32') {
            // Windows: Use tasklist to find DaMuse processes
            exec('tasklist /FI "IMAGENAME eq node.exe" /FO CSV', (error, stdout) => {
                if (error) {
                    console.warn('⚠️ [PROCESS_CHECK] Could not check for existing processes:', error.message);
                    resolve(false);
                    return;
                }
                
                const lines = stdout.split('\n');
                let daMuseProcesses = 0;
                
                for (const line of lines) {
                    if (line.includes('DaMuse.js') || line.includes('damuse')) {
                        daMuseProcesses++;
                    }
                }
                
                if (daMuseProcesses > 1) {
                    console.error('❌ [PROCESS_CHECK] Multiple DaMuse instances detected!');
                    console.error('❌ [PROCESS_CHECK] Please stop other instances before starting a new one.');
                    console.error('❌ [PROCESS_CHECK] Use the start-daMuse.ps1 script to manage processes safely.');
                    resolve(true);
                } else {
                    resolve(false);
                }
            });
        } else {
            // Unix/Linux: Use ps to find DaMuse processes
            exec('ps aux | grep -v grep | grep DaMuse', (error, stdout) => {
                if (error) {
                    console.warn('⚠️ [PROCESS_CHECK] Could not check for existing processes:', error.message);
                    resolve(false);
                    return;
                }
                
                const lines = stdout.trim().split('\n').filter(line => line.length > 0);
                
                if (lines.length > 1) {
                    console.error('❌ [PROCESS_CHECK] Multiple DaMuse instances detected!');
                    console.error('❌ [PROCESS_CHECK] Please stop other instances before starting a new one.');
                    resolve(true);
                } else {
                    resolve(false);
                }
            });
        }
    });
}

// Check for existing processes before starting
console.log('🔍 [PROCESS_CHECK] Checking for existing DaMuse processes...');
checkForExistingProcesses().then(hasExisting => {
    if (hasExisting) {
        console.error('🛑 [PROCESS_CHECK] Exiting to prevent conflicts...');
        process.exit(1);
    } else {
        console.log('✅ [PROCESS_CHECK] No conflicting processes found, starting DaMuse...');
    }
}).catch(error => {
    console.warn('⚠️ [PROCESS_CHECK] Process check failed, continuing anyway:', error.message);
});

// Set FFmpeg path for Discord.js voice
const path = require('path');
const fs = require('fs');

// Use modern @ffmpeg-installer/ffmpeg (more reliable and maintained)
let FFMPEG_PATH;
try {
    FFMPEG_PATH = require('@ffmpeg-installer/ffmpeg').path;
    console.log(`🔧 [SETUP] Using @ffmpeg-installer/ffmpeg: ${FFMPEG_PATH}`);
} catch (error) {
    // Fallback to local FFmpeg
    FFMPEG_PATH = path.join(__dirname, 'ffmpeg', 'bin', 'ffmpeg.exe');
    console.log(`🔧 [SETUP] Using local FFmpeg: ${FFMPEG_PATH}`);
}

if (fs.existsSync(FFMPEG_PATH)) {
    // Set environment variables for FFmpeg
    process.env.FFMPEG_PATH = FFMPEG_PATH;
    process.env.FFMPEG_BINARY = FFMPEG_PATH;
    process.env.FFMPEG_EXECUTABLE = FFMPEG_PATH;
    
    // Also set global variables for fallback
    global.FFMPEG_PATH = FFMPEG_PATH;
    global.FFMPEG_BINARY = FFMPEG_PATH;
    global.FFMPEG_EXECUTABLE = FFMPEG_PATH;
    
    // Configure FFmpeg path for @discordjs/voice library
    try {
        const { register } = require('@discordjs/voice');
        if (typeof register === 'function') {
            register(FFMPEG_PATH, 'ffmpeg');
            register(FFMPEG_PATH, 'ffprobe');
            console.log(`🔧 [DEBUG] FFmpeg and FFprobe registered with @discordjs/voice`);
        } else {
            console.warn(`🔧 [DEBUG] register function not available in @discordjs/voice`);
            // Set as global variable for fallback
            global.FFMPEG_PATH = FFMPEG_PATH;
        }
    } catch (error) {
        console.warn(`🔧 [DEBUG] Failed to register FFmpeg with @discordjs/voice:`, error.message);
        // Fallback: try to set it as a global variable
        global.FFMPEG_PATH = FFMPEG_PATH;
    }
    
    console.log(`🔧 [SETUP] FFmpeg path set: ${FFMPEG_PATH}`);
    console.log(`🔧 [DEBUG] FFmpeg exists: ${fs.existsSync(FFMPEG_PATH)}`);
    console.log(`🔧 [DEBUG] FFmpeg path set as environment variable`);
} else {
    console.error(`🔧 [SETUP] ❌ FFmpeg not found at: ${FFMPEG_PATH}`);
}

/**
 * Initialize Discord Client with Required Intents
 * 
 * The client is configured with specific intents to enable:
 * - Guild management (servers)
 * - Message handling (for text commands)
 * - Message content access (for command parsing)
 * - Voice state tracking (for music functionality)
 */
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,           // Access to guild (server) information
        GatewayIntentBits.GuildMessages,    // Access to guild messages
        GatewayIntentBits.MessageContent,   // Access to message content for command parsing
        GatewayIntentBits.GuildVoiceStates  // Access to voice channel states for music
    ]
});

// Create a collection to store all registered commands
// This allows for efficient command lookup during interactions
client.commands = new Collection();

/**
 * Command Loading System
 * 
 * This section dynamically loads all command files from the 'cogs' directory.
 * Each command file must export an object with 'data' and 'execute' properties.
 * Commands are stored in a Collection for efficient lookup during interactions.
 */

// Define the path to the cogs directory containing all command files
const cogsPath = join(__dirname, 'cogs');
// Read all JavaScript files from the cogs directory
const commandFiles = readdirSync(cogsPath).filter(file => file.endsWith('.js'));

// Iterate through each command file and load it into the bot
for (const file of commandFiles) {
    const filePath = join(cogsPath, file);
    const command = require(filePath);
    
    // Validate that the command has the required properties
    if (command.data && command.execute) {
        // Store the command in the collection using its name as the key
        client.commands.set(command.data.name, command);
        console.log(`[INFO] Loaded command: ${command.data.name}`);
    } else {
        // Log a warning for invalid command files
        console.warn(`[WARNING] Command ${file} is missing required "data" or "execute" property`);
    }
}

/**
 * Bot Ready Event Handler
 * 
 * This event fires once when the bot successfully connects to Discord.
 * It handles initial setup tasks like database connection and
 * periodic maintenance tasks.
 */
client.once(Events.ClientReady, async readyClient => {
    console.log(`Ready! Logged in as ${readyClient.user.tag}`);
    
    // Clean up any existing voice connections from previous sessions
    console.log('🧹 [CLEANUP] Cleaning up any existing voice connections...');
    const { getVoiceConnection, joinVoiceChannel } = require('@discordjs/voice');
    
    // Clean up queue system first
    queues.cleanupAllConnections();
    
    // Get all guilds the bot is in and clean up any existing connections
    for (const guild of readyClient.guilds.cache.values()) {
        const member = guild.members.cache.get(readyClient.user.id);
        const voiceChannel = member?.voice.channel;

        if (voiceChannel) {
            console.log(`🧹 [CLEANUP] Found bot in voice channel "${voiceChannel.name}" in guild "${guild.name}". Attempting to disconnect.`);
            try {
                // Forcibly join and then immediately destroy to clear the state.
                const connection = joinVoiceChannel({
                    channelId: voiceChannel.id,
                    guildId: guild.id,
                    adapterCreator: guild.voiceAdapterCreator,
                });
                connection.destroy();
                console.log(`🧹 [CLEANUP] ✅ Successfully cleared lingering connection for guild ${guild.id}`);
            } catch (error) {
                console.error(`🧹 [CLEANUP] ❌ Failed to clear lingering connection for guild ${guild.id}:`, error);
            }
        } else {
            // Also check with getVoiceConnection for any tracked connections that might be stale
            const existingConnection = getVoiceConnection(guild.id);
            if (existingConnection) {
                console.log(`🧹 [CLEANUP] Found existing connection object for guild ${guild.id}, destroying...`);
                try {
                    existingConnection.destroy();
                    console.log(`🧹 [CLEANUP] ✅ Cleaned up connection for guild ${guild.id}`);
                } catch (error) {
                    console.error(`🧹 [CLEANUP] ❌ Failed to clean up connection for guild ${guild.id}:`, error);
                }
            }
        }
    }
    
    // Establish database connection for data persistence
    try {
        await database.connect();
        console.log('✅ Database connected successfully');
    } catch (error) {
        console.error('❌ Failed to connect to database:', error);
    }
    
    // Set up periodic cleanup for autoplay manager
    // This runs every hour to clean up old data and optimize performance
    setInterval(() => {
        autoplayManager.cleanup();
    }, 60 * 60 * 1000); // Clean up every hour (60 minutes * 60 seconds * 1000 milliseconds)
});

/**
 * Interaction Event Handler
 * 
 * This event handler processes all Discord interactions including:
 * - Slash commands (chat input commands)
 * - Context menu commands (right-click menu commands)
 * 
 * It includes comprehensive error handling and user feedback.
 */
client.on(Events.InteractionCreate, async interaction => {
    // Handle slash commands (commands triggered with /)
    if (interaction.isChatInputCommand()) {
        const command = client.commands.get(interaction.commandName);

        // Check if the command exists in our collection
        if (!command) {
            console.error(`No command matching ${interaction.commandName} was found.`);
            return;
        }

        // Execute the command with error handling
        try {
            await command.execute(interaction);
        } catch (error) {
            console.error(error);
            // Send error message to user (flags: 64 = only visible to the user)
            try {
                if (interaction.replied || interaction.deferred) {
                    await interaction.followUp({ content: 'There was an error while executing this command!', flags: 64 });
                } else {
                    await interaction.reply({ content: 'There was an error while executing this command!', flags: 64 });
                }
            } catch (replyError) {
                // If we can't reply to the interaction, just log it
                console.error('Failed to send error response:', replyError.message);
            }
        }
    } 
    // Handle context menu commands (right-click menu interactions)
    else if (interaction.isContextMenuCommand()) {
        const command = client.commands.get(interaction.commandName);

        // Check if the context menu command exists
        if (!command) {
            console.error(`No context menu command matching ${interaction.commandName} was found.`);
            return;
        }

        // Execute the context menu command with error handling
        try {
            await command.execute(interaction);
        } catch (error) {
            console.error(error);
            // Send error message to user (flags: 64 = only visible to the user)
            try {
                if (interaction.replied || interaction.deferred) {
                    await interaction.followUp({ content: 'There was an error while executing this command!', flags: 64 });
                } else {
                    await interaction.reply({ content: 'There was an error while executing this command!', flags: 64 });
                }
            } catch (replyError) {
                // If we can't reply to the interaction, just log it
                console.error('Failed to send error response:', replyError.message);
            }
        }
    }
});

/**
 * Process Cleanup Handlers
 * 
 * These handlers ensure proper cleanup of voice connections when the bot
 * is terminated or restarted, preventing connection state issues.
 */

// Handle graceful shutdown on process termination
process.on('SIGINT', async () => {
    console.log('🛑 [SHUTDOWN] Received SIGINT, cleaning up voice connections...');
    const { getVoiceConnection } = require('@discordjs/voice');
    
    // Clean up queue system first
    queues.cleanupAllConnections();
    
    // Clean up all voice connections
    for (const [guildId, guild] of client.guilds.cache) {
        const connection = getVoiceConnection(guildId);
        if (connection) {
            try {
                connection.destroy();
                console.log(`🛑 [SHUTDOWN] ✅ Cleaned up connection for guild ${guildId}`);
            } catch (error) {
                console.error(`🛑 [SHUTDOWN] ❌ Failed to clean up connection for guild ${guildId}:`, error);
            }
        }
    }
    
    console.log('🛑 [SHUTDOWN] Cleanup complete, exiting...');
    process.exit(0);
});

// Handle graceful shutdown on process termination (Windows)
process.on('SIGTERM', async () => {
    console.log('🛑 [SHUTDOWN] Received SIGTERM, cleaning up voice connections...');
    const { getVoiceConnection } = require('@discordjs/voice');
    
    // Clean up queue system first
    queues.cleanupAllConnections();
    
    // Clean up all voice connections
    for (const [guildId, guild] of client.guilds.cache) {
        const connection = getVoiceConnection(guildId);
        if (connection) {
            try {
                connection.destroy();
                console.log(`🛑 [SHUTDOWN] ✅ Cleaned up connection for guild ${guildId}`);
            } catch (error) {
                console.error(`🛑 [SHUTDOWN] ❌ Failed to clean up connection for guild ${guildId}:`, error);
            }
        }
    }
    
    console.log('🛑 [SHUTDOWN] Cleanup complete, exiting...');
    process.exit(0);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
    console.error('💥 [FATAL] Uncaught Exception:', error);
    console.log('🛑 [SHUTDOWN] Cleaning up due to uncaught exception...');
    const { getVoiceConnection } = require('@discordjs/voice');
    
    // Clean up queue system first
    queues.cleanupAllConnections();
    
    // Clean up all voice connections
    for (const [guildId, guild] of client.guilds.cache) {
        const connection = getVoiceConnection(guildId);
        if (connection) {
            try {
                connection.destroy();
            } catch (cleanupError) {
                console.error(`🛑 [SHUTDOWN] ❌ Failed to clean up connection for guild ${guildId}:`, cleanupError);
            }
        }
    }
    
    process.exit(1);
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
    console.error('💥 [FATAL] Unhandled Rejection at:', promise, 'reason:', reason);
    console.log('🛑 [SHUTDOWN] Cleaning up due to unhandled rejection...');
    const { getVoiceConnection } = require('@discordjs/voice');
    
    // Clean up queue system first
    queues.cleanupAllConnections();
    
    // Clean up all voice connections
    for (const [guildId, guild] of client.guilds.cache) {
        const connection = getVoiceConnection(guildId);
        if (connection) {
            try {
                connection.destroy();
            } catch (cleanupError) {
                console.error(`🛑 [SHUTDOWN] ❌ Failed to clean up connection for guild ${guildId}:`, cleanupError);
            }
        }
    }
    
    process.exit(1);
});

/**
 * Bot Login
 * 
 * Authenticate and connect the bot to Discord using the token
 * from the environment variables. This starts the bot's operation.
 */
client.login(process.env.DISCORD_TOKEN);
