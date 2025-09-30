/**
 * Database Connection Manager - MongoDB Integration
 * 
 * This module handles MongoDB connection management with automatic
 * reconnection, error handling, and connection validation. It provides
 * a robust database connection layer for the Discord bot.
 * 
 * Features:
 * - Automatic connection and reconnection
 * - Connection validation and health checks
 * - Error handling and retry logic
 * - Connection state monitoring
 * - Graceful disconnection
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

const mongoose = require('mongoose');

/**
 * Database Class
 * 
 * Manages MongoDB connection with automatic reconnection and error handling.
 */
class Database {
    /**
     * Constructor - Initialize database connection settings
     * 
     * Sets up MongoDB connection options and retry configuration.
     */
    constructor() {
        this.uri = process.env.MONGO_URI;
        this.options = {
            useNewUrlParser: true,
            useUnifiedTopology: true,
            maxPoolSize: 10,
            serverSelectionTimeoutMS: 5000,
            socketTimeoutMS: 45000,
        };
        this.connectionAttempts = 0;
        this.maxRetries = 30;
    }

    /**
     * Connect to MongoDB
     * 
     * Establishes connection to MongoDB with automatic retry logic.
     * Handles connection errors and implements exponential backoff.
     * 
     * @throws {Error} If max retry attempts are reached
     */
    async connect() {
        this.connectionAttempts++;
        
        try {
            console.log(`[DATABASE] Connection attempt ${this.connectionAttempts}/${this.maxRetries}`);
            
            if (!this.uri) {
                throw new Error('MongoDB URI is not defined in environment variables');
            }
            
            await mongoose.connect(this.uri, this.options);
            
            // Wait for the connection to be truly ready
            await new Promise((resolve, reject) => {
                if (mongoose.connection.readyState === 1) {
                    resolve();
                } else {
                    mongoose.connection.once('connected', resolve);
                    mongoose.connection.once('error', reject);
                    // Timeout after 10 seconds
                    setTimeout(() => reject(new Error('Database connection timeout')), 10000);
                }
            });
            
            console.log('✅ [DATABASE] Connected to MongoDB successfully');
            
            // Reset connection attempts on successful connection
            this.connectionAttempts = 0;
            
            mongoose.connection.on('error', error => {
                console.error('[DATABASE] MongoDB connection error:', error);
            });

            mongoose.connection.on('disconnected', () => {
                console.warn('⚠️  [DATABASE] MongoDB disconnected. Attempting to reconnect...');
                if (this.connectionAttempts < this.maxRetries) {
                    setTimeout(() => this.connect(), 5000);
                } else {
                    console.error('❌ [DATABASE] Max database reconnection attempts reached');
                }
            });

        } catch (error) {
            console.error(`❌ [DATABASE] Failed to connect to MongoDB (attempt ${this.connectionAttempts}/${this.maxRetries}):`, error.message);
            
            if (this.connectionAttempts < this.maxRetries) {
                console.log(`⏳ [DATABASE] Retrying connection in 5 seconds...`);
                setTimeout(() => this.connect(), 5000);
            } else {
                console.error('❌ [DATABASE] Max database connection attempts reached. Bot will start without database.');
                throw error;
            }
        }
    }

    /**
     * Disconnect from MongoDB
     * 
     * Gracefully disconnects from the MongoDB database.
     * 
     * @throws {Error} If disconnection fails
     */
    async disconnect() {
        try {
            await mongoose.disconnect();
            console.log('[DATABASE] Disconnected from MongoDB');
        } catch (error) {
            console.error('[DATABASE] Error disconnecting from MongoDB:', error);
            throw error;
        }
    }

    /**
     * Validate Connection
     * 
     * Validates that the database connection is active and responsive.
     * 
     * @returns {boolean} True if connection is valid
     * @throws {Error} If connection is invalid or unresponsive
     */
    async validateConnection() {
        if (mongoose.connection.readyState !== 1) {
            throw new Error('Database connection not established');
        }
        
        // Test the connection by running a simple query
        try {
            await mongoose.connection.db.admin().ping();
            return true;
        } catch (error) {
            throw new Error(`Database connection validation failed: ${error.message}`);
        }
    }
}

module.exports = new Database();
