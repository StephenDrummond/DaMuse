/**
 * TEMPORARY DATABASE CONNECTION - IN-MEMORY DATABASE
 * 
 * ⚠️  WARNING: THIS IS TEMPORARY CODE FOR TESTING PURPOSES ONLY ⚠️
 * 
 * This file provides a temporary database connection that uses in-memory storage
 * instead of MongoDB. All data will be lost when the bot restarts.
 * 
 * TO CLEAN UP:
 * 1. Delete this file: utils/tempDatabaseConnection.js
 * 2. Restore original database.js from git
 * 3. Update DaMuse.js to use original database connection
 */

const tempDb = require('./tempDatabase');

class TempDatabaseConnection {
    constructor() {
        this.uri = 'temp://in-memory-database';
        this.connectionAttempts = 0;
        this.maxRetries = 1; // No need for retries with in-memory DB
    }

    async connect() {
        this.connectionAttempts++;
        
        try {
            console.log(`🗄️  [TEMP_DB] Initializing in-memory database (attempt ${this.connectionAttempts}/${this.maxRetries})`);
            
            // Simulate connection delay
            await new Promise(resolve => setTimeout(resolve, 100));
            
            console.log('✅ [TEMP_DB] In-memory database initialized successfully');
            console.log('⚠️  [TEMP_DB] WARNING: All data will be lost when the bot restarts!');
            
            // Reset connection attempts on successful connection
            this.connectionAttempts = 0;
            
        } catch (error) {
            console.error(`❌ [TEMP_DB] Failed to initialize in-memory database:`, error.message);
            throw error;
        }
    }

    async disconnect() {
        try {
            tempDb.clear();
            console.log('🗑️  [TEMP_DB] In-memory database cleared and disconnected');
        } catch (error) {
            console.error('[TEMP_DB] Error clearing in-memory database:', error);
            throw error;
        }
    }

    async validateConnection() {
        // Always return true for in-memory database
        return true;
    }

    // Get database statistics
    getStats() {
        return tempDb.getStats();
    }

    // Clear all data
    clear() {
        tempDb.clear();
    }
}

module.exports = new TempDatabaseConnection();
