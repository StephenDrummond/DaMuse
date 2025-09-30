/**
 * Spotify Utilities - Music Platform Integration
 * 
 * This module provides integration with the Spotify Web API for music
 * discovery, track information retrieval, and playlist management.
 * It handles Spotify authentication and API interactions.
 * 
 * Features:
 * - Spotify API authentication and initialization
 * - Track information retrieval from Spotify URLs
 * - URL validation and track ID extraction
 * - Album and artist information access
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

const SpotifyWebApi = require('spotify-web-api-node');

/**
 * Spotify Utils Class
 * 
 * Handles all Spotify API interactions including authentication,
 * track information retrieval, and URL processing.
 */
class SpotifyUtils {
    /**
     * Constructor - Initialize Spotify API client
     * 
     * Sets up the Spotify Web API client with credentials from environment variables.
     */
    constructor() {
        this.spotifyApi = new SpotifyWebApi({
            clientId: process.env.SPOTIFY_CLIENT_ID,
            clientSecret: process.env.SPOTIFY_CLIENT_SECRET,
        });
    }

    /**
     * Initialize Spotify API
     * 
     * Authenticates with Spotify using client credentials flow
     * and sets the access token for API requests.
     */
    async initialize() {
        try {
            const data = await this.spotifyApi.clientCredentialsGrant();
            this.spotifyApi.setAccessToken(data.body['access_token']);
            console.log('Spotify API initialized successfully');
        } catch (error) {
            console.error('Error initializing Spotify API:', error);
        }
    }

    /**
     * Get Track Information
     * 
     * Retrieves detailed information about a Spotify track from its URL.
     * 
     * @param {string} spotifyUrl - Spotify track URL
     * @returns {Object|null} Track information or null if failed
     */
    async getTrackInfo(spotifyUrl) {
        try {
            // Extract track ID from URL
            const trackId = this.extractTrackId(spotifyUrl);
            if (!trackId) {
                throw new Error('Invalid Spotify URL');
            }

            const track = await this.spotifyApi.getTrack(trackId);
            
            return {
                name: track.body.name,
                artists: track.body.artists.map(artist => artist.name),
                album: track.body.album.name,
                duration_ms: track.body.duration_ms,
                url: track.body.external_urls.spotify,
                preview_url: track.body.preview_url,
                images: track.body.album.images
            };
        } catch (error) {
            console.error('Error getting Spotify track info:', error);
            return null;
        }
    }

    /**
     * Extract Track ID
     * 
     * Extracts the track ID from a Spotify URL.
     * 
     * @param {string} url - Spotify URL
     * @returns {string|null} Track ID or null if invalid
     */
    extractTrackId(url) {
        const match = url.match(/\/track\/([a-zA-Z0-9]+)/);
        return match ? match[1] : null;
    }

    /**
     * Is Valid Spotify URL
     * 
     * Validates if a URL is a valid Spotify track URL.
     * 
     * @param {string} url - URL to validate
     * @returns {boolean} True if valid Spotify track URL
     */
    isValidSpotifyUrl(url) {
        return /^https:\/\/open\.spotify\.com\/track\//.test(url);
    }
}

module.exports = { SpotifyUtils: new SpotifyUtils() };

