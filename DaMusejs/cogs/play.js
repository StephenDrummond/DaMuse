/**
 * Play Command - Music Playback System
 * 
 * This command handles music playback by searching for songs, adding them to the queue,
 * and managing voice connections. It integrates with YouTube for song discovery
 * and provides seamless music streaming functionality.
 * 
 * Features:
 * - Searches and plays songs from YouTube
 * - Manages voice channel connections
 * - Handles audio streaming with FFmpeg
 * - Integrates with music queue system
 * - Records song data in database
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

// ⚠️  TEMPORARY: Using in-memory database models for testing
// Import Discord.js components for slash command and embed creation
const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
// Import Discord.js voice utilities for audio playback
const { joinVoiceChannel, createAudioPlayer, createAudioResource, AudioPlayerStatus, VoiceConnectionStatus, getVoiceConnection } = require('@discordjs/voice');
// Import the base command class that provides common functionality
const { BaseCommand } = require('../utils/commandTemplate');
// Import error handling utilities for validation errors
const { createValidationError } = require('../utils/errorHandler');
// Import helper functions for command validation
const { isInVoiceChannel } = require('../utils/commandHelpers');
// Import music queue system for managing song queues
const { queues } = require('../music_state/queues');
// Import inactivity timer system for auto-disconnect
const { inactivity_timers } = require('../music_state/inactivity');
// Import YouTube utilities for song search and streaming
const { YouTubeUtils } = require('../utils/youtube');
// Import temporary database models (will be replaced with MongoDB models)
const Song = require('../models/tempSong');
const UserPreference = require('../models/tempUserPreference');
const MusicInteraction = require('../models/tempMusicInteraction');

// FFmpeg options optimized for Discord voice channels with reduced stuttering
// These options ensure smooth audio playback with minimal buffering
const FFMPEG_OPTIONS = {
    // Input options: enable reconnection and handle stream issues gracefully
    // Removed -analyzeduration 0 as it can cause issues with some streams
    before_options: '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel 0',
    // Output options: convert to Opus format optimized for Discord voice
    options: '-vn -acodec libopus -b:a 96k -ar 48000 -ac 2 -f opus -application audio'
};

// FFmpeg executable path for audio processing
// Use modern @ffmpeg-installer/ffmpeg (more reliable and maintained)
let FFMPEG_PATH;
try {
    FFMPEG_PATH = require('@ffmpeg-installer/ffmpeg').path;
} catch (error) {
    // Fallback to local FFmpeg
    FFMPEG_PATH = require('path').join(__dirname, '..', 'ffmpeg', 'bin', 'ffmpeg.exe');
}

// Check FFmpeg path and set environment variable
const fs = require('fs');

console.log(`🔧 [DEBUG] FFmpeg path: ${FFMPEG_PATH}`);
console.log(`🔧 [DEBUG] FFmpeg exists: ${fs.existsSync(FFMPEG_PATH)}`);

if (fs.existsSync(FFMPEG_PATH)) {
    // Set FFmpeg path as environment variable for Discord.js voice
    process.env.FFMPEG_PATH = FFMPEG_PATH;
    process.env.FFMPEG_BINARY = FFMPEG_PATH;
    process.env.FFMPEG_EXECUTABLE = FFMPEG_PATH;
    console.log(`🔧 [DEBUG] FFmpeg path set as environment variable`);
} else {
    console.error(`🔧 [DEBUG] ❌ FFmpeg not found at: ${FFMPEG_PATH}`);
}

/**
 * Play Command Class
 * 
 * Handles the /play slash command which searches for songs and plays them
 * in the voice channel, managing the entire music playback pipeline.
 */
class PlayCommand extends BaseCommand {
    /**
     * Constructor - Initialize the play command
     * 
     * Sets up the slash command with name, description, and a required
     * string option for song search terms or YouTube URLs.
     */
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('play')                                    // Command name (used as /play)
                .setDescription('Play a song or add it to the queue')
                .addStringOption(option =>                          // Add required string option
                    option.setName('search')                        // Option name
                        .setDescription('Song name or YouTube URL') // Option description
                        .setRequired(true))                        // Make option required
        );
    }

    /**
     * Defer Reply Setting
     * 
     * Indicates that this command should defer its reply since it may take
     * time to search for and process the song before responding.
     * 
     * @returns {boolean} True to defer the reply
     */
    shouldDeferReply() {
        return true; // Defer to prevent timeout during song search
    }

    /**
     * Input Validation
     * 
     * Validates that the user is in a voice channel (required for music playback)
     * and extracts the search term from the interaction.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing the search term
     * @throws {Error} If user is not in a voice channel or no search term provided
     */
    async validateInput(interaction) {
        // Ensure user is in a voice channel (required for music playback)
        if (!isInVoiceChannel(interaction.member)) {
            throw createValidationError('You must be in a voice channel to play music!');
        }

        // Extract and validate the search term
        const search = interaction.options.getString('search');
        if (!search) {
            throw createValidationError('Please provide a song name or link.');
        }

        return { search };
    }

    /**
     * Command Execution
     * 
     * Processes the play request by:
     * 1. Searching for the song using YouTube
     * 2. Saving song data to database
     * 3. Adding song to the queue
     * 
     * Note: Voice connection and playback are handled asynchronously
     * to prevent interaction timeout issues.
     * 
     * @param {Object} interaction - Discord interaction object
     * @returns {Object} Object containing song information and database record
     * @throws {Error} If song search fails
     */
    async executeCommand(interaction) {
        const { search } = await this.validateInput(interaction);

        try {
            console.log(`🔍 [DEBUG] Starting song search for: ${search}`);
            
            // Search for the song using YouTube utility
            // This handles both search terms and direct YouTube URLs
            const songInfo = await YouTubeUtils.searchAndGetFirst(search);
            console.log(`🔍 [DEBUG] Song found: ${songInfo.title}`);

            // Save song to database for tracking and recommendations
            const song = await Song.findOrCreate({
                title: songInfo.title,                    // Song title
                artist: songInfo.author || 'Unknown Artist', // Artist name (fallback if unknown)
                url: songInfo.url,                        // YouTube URL
                thumbnail: songInfo.thumbnail,            // Song thumbnail image
                duration: songInfo.duration,            // Song duration in milliseconds
                genre: 'Unknown',                        // Genre (could be enhanced with detection)
                mood: 'Neutral',                         // Mood classification
                energy: 5                                // Energy level (1-10 scale)
            });

            // Add song to the music queue for this guild
            const guildId = interaction.guild.id;
            console.log(`📋 [DEBUG] Adding song to queue for guild ${guildId}`);
            queues.addToQueue(guildId, songInfo);
            console.log(`📋 [DEBUG] Queue length: ${queues.getQueue(guildId).length}`);

            // Return immediately to avoid interaction timeout
            return { songInfo, song };
        } catch (error) {
            console.error('Error in play command:', error);
            throw createValidationError('Error retrieving track. Please check the URL or try a different search term.');
        }
    }

    /**
     * Send Response
     * 
     * Sends a deferred response and handles voice connection asynchronously.
     * This prevents interaction timeout issues.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing song information
     */
    async sendResponse(interaction, result) {
        // Check if interaction has already been replied to
        if (interaction.replied) {
            console.warn('Interaction already replied to, skipping response');
            return;
        }

        // Create embed showing the queued song
        const embed = new EmbedBuilder()
            .setTitle('🎵 Song Queued')                    // Embed title
            .setDescription(`**${result.songInfo.title}**`) // Song title
            .setThumbnail(result.songInfo.thumbnail)      // Song thumbnail
            .setColor(0x00ff00);                          // Green color for success

        try {
            // Send deferred response (since we deferred earlier)
            await interaction.editReply({ embeds: [embed] });
        } catch (error) {
            console.error('Error sending response:', error);
            return; // Don't continue if we can't send the response
        }
        
        // Handle voice connection and playback asynchronously
        // Don't await this to avoid blocking the response
        this.handlePlayback(interaction, result).catch(error => {
            console.error('Error in async playback handling:', error);
            // Try to send a follow-up message if possible
            interaction.followUp('❌ Error setting up voice connection. Please try again.').catch(() => {
                // If we can't send a follow-up, just log it
                console.error('Failed to send error follow-up');
            });
        });
    }
    
    /**
     * Handle Playback
     * 
     * Handles voice connection and audio playback after the response is sent.
     * This prevents interaction timeout issues.
     * 
     * @param {Object} interaction - Discord interaction object
     * @param {Object} result - Result from executeCommand containing song information
     */
    async handlePlayback(interaction, result) {
        try {
            const guildId = interaction.guild.id;
            
            // Ensure bot is connected to the voice channel
            console.log(`📋 [DEBUG] Ensuring voice connection...`);
            await this.ensureVoiceConnection(interaction);

            // Get the connection and verify it's ready
            const connection = getVoiceConnection(guildId);
            console.log(`📋 [DEBUG] Connection status: ${connection?.state?.status || 'none'}`);
            console.log(`📋 [DEBUG] Is currently playing: ${queues.isPlaying(guildId)}`);
            
            // Only proceed if connection is ready
            if (connection && connection.state.status === VoiceConnectionStatus.Ready) {
                if (!queues.isPlaying(guildId)) {
                    console.log(`📋 [DEBUG] Starting playback...`);
                    await this.playNextSong(interaction);
                } else {
                    console.log(`📋 [DEBUG] Already playing, song queued`);
                }
            } else {
                console.log(`📋 [DEBUG] Connection not ready, status: ${connection?.state?.status || 'none'}`);
                console.log(`📋 [DEBUG] Waiting for connection to be ready...`);
                
                // Wait for connection to be ready with timeout
                try {
                    await this.waitForConnectionReady(connection, guildId);
                    console.log(`📋 [DEBUG] Connection is now ready, starting playback...`);
                    
                    if (!queues.isPlaying(guildId)) {
                        await this.playNextSong(interaction);
                    } else {
                        console.log(`📋 [DEBUG] Already playing, song queued`);
                    }
                } catch (timeoutError) {
                    console.error(`📋 [DEBUG] ❌ Connection timeout:`, timeoutError);
                    await interaction.followUp('❌ Failed to connect to voice channel. Please try again.');
                }
            }
        } catch (error) {
            console.error('Error in playback handling:', error);
            await interaction.followUp('❌ Error setting up voice connection. Please try again.');
        }
    }

    /**
     * Ensure Voice Connection
     * 
     * Establishes a voice connection to the user's voice channel if one doesn't exist.
     * Sets up the audio player and event handlers for seamless music playback.
     * Includes proper connection state handling and timeout protection.
     * 
     * @param {Object} interaction - Discord interaction object
     */
    async ensureVoiceConnection(interaction) {
        const guildId = interaction.guild.id;
        const voiceChannel = interaction.member.voice.channel;
        let connection = getVoiceConnection(guildId);

        console.log(`🔊 [DEBUG] Ensuring voice connection for guild ${guildId}...`);
        console.log(`🔊 [DEBUG] Voice channel: ${voiceChannel?.name || 'None'} (ID: ${voiceChannel?.id})`);
        console.log(`🔊 [DEBUG] Existing connection: ${!!connection}`);

        // Clean up any existing connection that's in a bad state
        if (connection) {
            const status = connection.state.status;
            console.log(`🔊 [DEBUG] Existing connection status: ${status}`);
            
            // If connection is in a bad state, destroy it and create a new one
            if (status === VoiceConnectionStatus.Destroyed || 
                status === VoiceConnectionStatus.Disconnected ||
                status === VoiceConnectionStatus.Signalling) {
                console.log(`🔊 [DEBUG] Connection in bad state (${status}), destroying and recreating...`);
                try {
                    connection.destroy();
                    connection = null;
                    console.log('🔊 [DEBUG] ✅ Old connection destroyed');
                } catch (error) {
                    console.error('🔊 [DEBUG] ❌ Failed to destroy old connection:', error);
                }
            } else if (status === VoiceConnectionStatus.Ready) {
                console.log('🔊 [DEBUG] Connection is already ready, reusing...');
                return; // Connection is ready, no need to create a new one
            }
        }

        // Create new connection if one doesn't exist
        if (!connection) {
            console.log('🔊 [DEBUG] Creating new voice connection...');
            try {
                connection = joinVoiceChannel({
                    channelId: voiceChannel.id,                    // Target voice channel
                    guildId: guildId,                             // Guild ID
                    adapterCreator: interaction.guild.voiceAdapterCreator, // Voice adapter
                });

                console.log('🔊 [DEBUG] Voice connection created successfully');
                console.log(`🔊 [DEBUG] Connection state: ${connection.state.status}`);

                // Wait for connection to be ready with timeout
                await this.waitForConnectionReady(connection, guildId);

                // Set up audio player for this guild
                const player = createAudioPlayer();
                console.log('🔊 [DEBUG] Audio player created');
                
                // Subscribe player to connection BEFORE storing in queue system
                connection.subscribe(player);                     // Subscribe player to connection
                console.log('🔊 [DEBUG] Player subscribed to connection');
                
                // Store player in queue system AFTER subscription
                queues.setPlayer(guildId, player);                 // Store player in queue system
                console.log('🔊 [DEBUG] Player stored in queue system');
                
                // Verify the subscription is working
                console.log(`🔊 [DEBUG] Connection subscriber count: ${connection.state.subscription ? 1 : 0}`);
                console.log(`🔊 [DEBUG] Player state: ${player.state.status}`);

                // Handle player events for automatic queue progression
                player.on(AudioPlayerStatus.Idle, () => {
                    console.log('🔊 [DEBUG] Audio player became idle, playing next song...');
                    // Automatically play next song when current song ends
                    this.playNextSong(interaction);
                });

                // Handle audio player errors
                player.on('error', error => {
                    console.error('🔊 [DEBUG] Audio player error:', error);
                });

                // Handle player state changes
                player.on('stateChange', (oldState, newState) => {
                    console.log(`🔊 [DEBUG] Player state changed: ${oldState.status} -> ${newState.status}`);
                });

                console.log('🔊 [DEBUG] Audio player setup complete');
            } catch (error) {
                console.error('🔊 [DEBUG] Failed to create voice connection:', error);
                throw error;
            }
        } else {
            console.log('🔊 [DEBUG] Voice connection already exists');
            console.log(`🔊 [DEBUG] Connection state: ${connection.state.status}`);
            
            // Ensure connection is ready
            if (connection.state.status !== VoiceConnectionStatus.Ready) {
                console.log('🔊 [DEBUG] Connection not ready, waiting for ready state...');
                await this.waitForConnectionReady(connection, guildId);
            }
        }
    }

    /**
     * Wait for Connection Ready
     * 
     * Waits for a voice connection to reach the Ready state with timeout protection.
     * Prevents the bot from getting stuck in signalling state indefinitely.
     * 
     * @param {Object} connection - Voice connection object
     * @param {string} guildId - Guild ID for logging
     * @returns {Promise} Promise that resolves when connection is ready
     */
    async waitForConnectionReady(connection, guildId) {
        return new Promise((resolve, reject) => {
            const timeout = 10000; // 10 second timeout
            let timeoutId;
            
            console.log(`🔊 [DEBUG] Waiting for connection ready for guild ${guildId}...`);
            
            // Set up timeout
            timeoutId = setTimeout(() => {
                console.error(`🔊 [DEBUG] ❌ Connection timeout for guild ${guildId}`);
                reject(new Error('Voice connection timeout - connection did not become ready in time'));
            }, timeout);
            
            // Check if already ready
            if (connection.state.status === VoiceConnectionStatus.Ready) {
                console.log(`🔊 [DEBUG] ✅ Connection already ready for guild ${guildId}`);
                clearTimeout(timeoutId);
                resolve();
                return;
            }
            
            // Listen for state changes
            const stateChangeHandler = (oldState, newState) => {
                console.log(`🔊 [DEBUG] Connection state changed for guild ${guildId}: ${oldState.status} -> ${newState.status}`);
                
                if (newState.status === VoiceConnectionStatus.Ready) {
                    console.log(`🔊 [DEBUG] ✅ Connection ready for guild ${guildId}`);
                    clearTimeout(timeoutId);
                    connection.off('stateChange', stateChangeHandler);
                    resolve();
                } else if (newState.status === VoiceConnectionStatus.Disconnected || 
                          newState.status === VoiceConnectionStatus.Destroyed) {
                    console.error(`🔊 [DEBUG] ❌ Connection failed for guild ${guildId}: ${newState.status}`);
                    clearTimeout(timeoutId);
                    connection.off('stateChange', stateChangeHandler);
                    reject(new Error(`Voice connection failed: ${newState.status}`));
                }
            };
            
            connection.on('stateChange', stateChangeHandler);
        });
    }

    /**
     * Play Next Song
     * 
     * Retrieves the next song from the queue and starts playback.
     * Handles stream creation, audio resource setup, and playback initiation.
     * Also manages inactivity timers when the queue is empty.
     * 
     * @param {Object} interaction - Discord interaction object
     */
    async playNextSong(interaction) {
        const guildId = interaction.guild.id;
        const song = queues.getNextSong(guildId);

        // Handle empty queue case
        if (!song) {
            await interaction.followUp('No more songs in the queue.');
            // Start inactivity timer to auto-disconnect after a period
            inactivity_timers.startTimer(interaction.guild, interaction.channel);
            return;
        }

        try {
            console.log(`🎵 [DEBUG] Attempting to play: ${song.title}`);
            console.log(`🎵 [DEBUG] Song URL: ${song.url}`);
            console.log(`🎵 [DEBUG] Song duration: ${song.duration}ms`);
            console.log(`🎵 [DEBUG] Song thumbnail: ${song.thumbnail}`);
            
            // Get audio stream from YouTube
            console.log('🎵 [DEBUG] Creating YouTube stream...');
            const stream = await YouTubeUtils.getStream(song); // Pass the whole song object
            console.log('🎵 [DEBUG] Stream created successfully');
            console.log(`🎵 [DEBUG] Stream type: ${stream.constructor.name}`);
            console.log(`🎵 [DEBUG] Stream readable: ${stream.readable}`);
            
            // Create audio resource with Discord-optimized options
            console.log('🎵 [DEBUG] Creating audio resource...');
            console.log(`🎵 [DEBUG] FFmpeg path: ${FFMPEG_PATH}`);
            console.log(`🎵 [DEBUG] FFmpeg options:`, FFMPEG_OPTIONS);
            
            const resource = createAudioResource(stream, {
                inputType: 'arbitrary',        // Arbitrary input type for YouTube streams
                inlineVolume: true,           // Enable volume control
                metadata: {                   // Song metadata for tracking
                    title: song.title,
                    url: song.url
                },
                // Discord-optimized FFmpeg options for smooth playback
                beforeOptions: FFMPEG_OPTIONS.before_options,
                options: FFMPEG_OPTIONS.options,
                // Ensure FFmpeg path is properly set with fallback
                ffmpegPath: FFMPEG_PATH || process.env.FFMPEG_PATH || global.FFMPEG_PATH,
                // Additional options for smooth playback
                silencePaddingFrames: 2,      // Reduce silence padding for less lag
                silenceRemaining: 1           // Reduce silence remaining for smoother transitions
            });
            console.log('🎵 [DEBUG] Audio resource created successfully');
            console.log(`🎵 [DEBUG] Resource type: ${resource.constructor.name}`);
            console.log(`🎵 [DEBUG] Resource metadata:`, resource.metadata);
            
            // Get the audio player for this guild
            const player = queues.getPlayer(guildId);
            console.log(`🎵 [DEBUG] Player found: ${!!player}`);
            console.log(`🎵 [DEBUG] Player state: ${player?.state?.status || 'unknown'}`);

            if (player) {
                console.log('🎵 [DEBUG] Starting audio playback...');
                
                // Add comprehensive event listeners to track playback
                const stateChangeHandler = (oldState, newState) => {
                    console.log(`🎵 [DEBUG] Player state changed: ${oldState.status} -> ${newState.status}`);
                    if (newState.status === AudioPlayerStatus.Playing) {
                        console.log('🎵 [DEBUG] ✅ Audio is now PLAYING!');
                    } else if (newState.status === AudioPlayerStatus.Paused) {
                        console.log('🎵 [DEBUG] ⏸️ Audio is PAUSED');
                    } else if (newState.status === AudioPlayerStatus.Idle) {
                        console.log('🎵 [DEBUG] ⏹️ Audio is IDLE');
                    } else if (newState.status === AudioPlayerStatus.Buffering) {
                        console.log('🎵 [DEBUG] 🔄 Audio is BUFFERING');
                    }
                };
                
                player.on('stateChange', stateChangeHandler);
                
                // Add error handling for the player with debug info
                player.on('error', (error) => {
                    console.error('🎵 [DEBUG] ❌ Audio player error:', error);
                    console.error('🎵 [DEBUG] Error details:', {
                        message: error.message,
                        code: error.code,
                        stack: error.stack
                    });
                    queues.setPlaying(guildId, false);
                });

                // Start playing the audio resource
                try {
                    player.play(resource);
                    queues.setPlaying(guildId, true); // Mark as currently playing
                    console.log('🎵 [DEBUG] Audio playback command sent');
                    
                    // Verify the resource is being processed
                    console.log(`🎵 [DEBUG] Resource started: ${resource.started}`);
                    console.log(`🎵 [DEBUG] Resource ended: ${resource.ended}`);
                } catch (playError) {
                    console.error('🎵 [DEBUG] ❌ Failed to start playback:', playError);
                    throw playError;
                }

                // Create and send "Now Playing" embed
                const embed = new EmbedBuilder()
                    .setTitle('🎵 Now Playing')           // Embed title
                    .setDescription(`**${song.title}**`)   // Song title
                    .setThumbnail(song.thumbnail)         // Song thumbnail
                    .setColor(0x00ff00);                  // Green color

                await interaction.followUp({ embeds: [embed] });
                console.log('🎵 [DEBUG] "Now Playing" embed sent');
            } else {
                console.error('🎵 [DEBUG] ❌ No audio player found for guild:', guildId);
                
                // Auto-leave voice channel when no player is available
                try {
                    console.log('🚪 [AUTO_LEAVE] Leaving voice channel - no audio player available...');
                    const connection = getVoiceConnection(guildId);
                    if (connection) {
                        connection.destroy();
                        console.log('🚪 [AUTO_LEAVE] ✅ Left voice channel - no audio player');
                    }
                    // Clean up queue state
                    queues.cleanupConnection(guildId);
                } catch (leaveError) {
                    console.error('🚪 [AUTO_LEAVE] ❌ Failed to leave voice channel:', leaveError);
                }
                
                await interaction.followUp('Error: No audio player available. Left voice channel.');
            }
        } catch (error) {
            console.error('🎵 [DEBUG] ❌ Error playing song:', error);
            console.error('🎵 [DEBUG] Error stack:', error.stack);
            
            // Auto-leave voice channel on playback failure
            try {
                console.log('🚪 [AUTO_LEAVE] Leaving voice channel due to playback error...');
                const connection = getVoiceConnection(guildId);
                if (connection) {
                    connection.destroy();
                    console.log('🚪 [AUTO_LEAVE] ✅ Left voice channel due to playback error');
                }
                // Clean up queue state
                queues.cleanupConnection(guildId);
            } catch (leaveError) {
                console.error('🚪 [AUTO_LEAVE] ❌ Failed to leave voice channel:', leaveError);
            }
            
            await interaction.followUp('Error playing the song.');
        }
    }
}

module.exports = new PlayCommand();
