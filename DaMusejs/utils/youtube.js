/**
 * YouTube Utilities - Video Processing and Streaming
 * 
 * This module provides YouTube video processing capabilities including
 * video information retrieval, URL validation, and audio stream generation
 * using the 'play-dl' library for enhanced stability.
 * 
 * @author DaMuse Team
 * @version 1.1.0
 */

const play = require('play-dl');
// const ytdl = require('@distube/ytdl-core');

/**
 * YouTube Utils Class
 * 
 * Handles all YouTube-related functionality including video processing,
 * stream generation, and URL validation using play-dl.
 */
class YouTubeUtils {
    /**
     * Get Video Information
     * 
     * Retrieves detailed information about a YouTube video from its URL.
     * 
     * @param {string} url - YouTube video URL
     * @returns {Object} Video information including title, duration, thumbnail, etc.
     * @throws {Error} If video info retrieval fails
     */
    static async getVideoInfo(url) {
        try {
            const videoInfo = await play.video_info(url);
            const videoDetails = videoInfo.video_details;
            
            return {
                title: videoDetails.title,
                url: videoDetails.url,
                duration: videoDetails.durationInSec * 1000,
                thumbnail: videoDetails.thumbnails[0]?.url,
                author: videoDetails.channel?.name || 'Unknown Artist'
            };
        } catch (error) {
            console.error('Error getting video info with play-dl:', error);
            throw error;
        }
    }

    /**
     * Is Valid URL
     * 
     * Validates if a string is a valid YouTube URL.
     * 
     * @param {string} string - URL string to validate
     * @returns {boolean} True if valid YouTube URL
     */
    static async isValidUrl(string) {
        try {
            const validation = await play.validate(string);
            return validation === 'yt_video';
        } catch (error) {
            return false;
        }
    }

    /**
     * Get Stream
     * 
     * Generates an audio stream from a YouTube video URL with optimized settings
     * for Discord voice channel playback using play-dl.
     * 
     * @param {string} url - YouTube video URL
     * @returns {ReadableStream} Audio stream
     */
    static async getStream(song) {
        const url = song.url;
        console.log(`🔗 [DEBUG] Creating stream for URL: ${url} using play-dl`);

        // Add a sanity check for the URL before calling play.stream
        if (!url || typeof url !== 'string' || !url.startsWith('http')) {
            console.error(`❌ [STREAM_ERROR] Invalid URL passed to getStream: ${url}`);
            throw new Error('Invalid URL provided for streaming.');
        }

        try {
            const stream = await play.stream(url, {
                discordPlayerCompatibility: true,
                quality: 2, // 'high' quality audio
            });

            console.log(`🔗 [DEBUG] Stream created successfully using play-dl`);
            
            // Add error handling with debug info
            stream.stream.on('error', (error) => {
                console.error('🔗 [DEBUG] Stream error:', error.message);
            });
            
            // Only log first data event to confirm stream is working
            let firstData = true;
            stream.stream.on('data', (chunk) => {
                if (firstData) {
                    console.log(`🔗 [DEBUG] ✅ Stream data received: ${chunk.length} bytes - AUDIO WORKING!`);
                    firstData = false;
                }
            });
            
            stream.stream.on('end', () => {
                console.log(`🔗 [DEBUG] Stream ended normally`);
            });
            
            stream.stream.on('close', () => {
                console.log('🔗 [DEBUG] Stream closed');
            });
            
            return stream.stream;
        } catch (error) {
            console.error('🔗 [DEBUG] Error creating stream with play-dl:', error);
            throw error;
        }
    }

    /**
     * Search And Get First
     * 
     * Handles search queries and returns the first result using play-dl.
     * 
     * @param {string} query - Search query or YouTube URL
     * @returns {Object} Video information
     * @throws {Error} If search fails
     */
    static async searchAndGetFirst(query) {
        try {
            const isUrl = await this.isValidUrl(query);
            if (isUrl) {
                console.log(`Direct URL detected, getting info...`);
                return await this.getVideoInfo(query);
            }
            
            console.log(`Searching for: ${query} using play-dl`);
            const searchResults = await play.search(query, {
                limit: 1,
                source: { youtube: 'video' }
            });
            
            if (!searchResults || searchResults.length === 0) {
                throw new Error(`No results found for query: "${query}"`);
            }
            
            const firstResult = searchResults[0];
            console.log(`Found video: ${firstResult.title}`);
            
            return {
                title: firstResult.title,
                url: firstResult.url,
                duration: firstResult.durationInSec * 1000,
                thumbnail: firstResult.thumbnails[0]?.url,
                author: firstResult.channel?.name || 'Unknown Artist'
            };
            
        } catch (error) {
            console.error('Error in search with play-dl:', error);
            throw new Error(`Could not find video for query: "${query}". Please try a different search term or provide a direct YouTube URL.`);
        }
    }
}

module.exports = { YouTubeUtils };

