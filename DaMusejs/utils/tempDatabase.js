/**
 * TEMPORARY IN-MEMORY DATABASE IMPLEMENTATION
 * 
 * ⚠️  WARNING: THIS IS TEMPORARY CODE FOR TESTING PURPOSES ONLY ⚠️
 * 
 * This file provides an in-memory database implementation that mimics MongoDB functionality
 * for testing the bot without requiring MongoDB setup. All data is stored in memory and
 * will be lost when the bot restarts.
 * 
 * TO CLEAN UP:
 * 1. Delete this file: utils/tempDatabase.js
 * 2. Delete these temporary model files: models/tempSong.js, models/tempUserPreference.js, models/tempMusicInteraction.js
 * 3. Restore original model files from git or recreate them
 * 4. Update DaMuse.js to use original database connection
 * 
 * This implementation is NOT suitable for production use!
 */

class TempDatabase {
    constructor() {
        this.collections = {
            songs: new Map(),
            userPreferences: new Map(),
            musicInteractions: new Map()
        };
        this.counters = {
            songs: 0,
            userPreferences: 0,
            musicInteractions: 0
        };
        console.log('🗄️  [TEMP_DB] In-memory database initialized (TEMPORARY - DATA WILL BE LOST ON RESTART)');
    }

    // Generate unique ID
    generateId(collection) {
        return `temp_${collection}_${++this.counters[collection]}_${Date.now()}`;
    }

    // Generic CRUD operations
    async create(collection, data) {
        const id = this.generateId(collection);
        const document = {
            _id: id,
            ...data,
            createdAt: new Date(),
            updatedAt: new Date()
        };
        this.collections[collection].set(id, document);
        return document;
    }

    async findById(collection, id) {
        return this.collections[collection].get(id) || null;
    }

    async findOne(collection, query) {
        for (const [id, doc] of this.collections[collection]) {
            if (this.matchesQuery(doc, query)) {
                return doc;
            }
        }
        return null;
    }

    async find(collection, query = {}, options = {}) {
        const results = [];
        for (const [id, doc] of this.collections[collection]) {
            if (this.matchesQuery(doc, query)) {
                results.push(doc);
            }
        }

        // Apply sorting
        if (options.sort) {
            results.sort((a, b) => {
                for (const [field, direction] of Object.entries(options.sort)) {
                    const aVal = this.getNestedValue(a, field);
                    const bVal = this.getNestedValue(b, field);
                    if (aVal < bVal) return direction === 1 ? -1 : 1;
                    if (aVal > bVal) return direction === 1 ? 1 : -1;
                }
                return 0;
            });
        }

        // Apply limit
        if (options.limit) {
            return results.slice(0, options.limit);
        }

        return results;
    }

    async updateOne(collection, query, update) {
        const doc = await this.findOne(collection, query);
        if (!doc) return { modifiedCount: 0 };
        
        const id = doc._id;
        const updatedDoc = {
            ...doc,
            ...update,
            updatedAt: new Date()
        };
        this.collections[collection].set(id, updatedDoc);
        return { modifiedCount: 1 };
    }

    async deleteOne(collection, query) {
        for (const [id, doc] of this.collections[collection]) {
            if (this.matchesQuery(doc, query)) {
                this.collections[collection].delete(id);
                return { deletedCount: 1 };
            }
        }
        return { deletedCount: 0 };
    }

    // Helper methods
    matchesQuery(doc, query) {
        for (const [key, value] of Object.entries(query)) {
            if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                // Handle MongoDB operators like $gte, $lte, etc.
                if (value.$gte !== undefined) {
                    if (this.getNestedValue(doc, key) < value.$gte) return false;
                }
                if (value.$lte !== undefined) {
                    if (this.getNestedValue(doc, key) > value.$lte) return false;
                }
                if (value.$gt !== undefined) {
                    if (this.getNestedValue(doc, key) <= value.$gt) return false;
                }
                if (value.$lt !== undefined) {
                    if (this.getNestedValue(doc, key) >= value.$lt) return false;
                }
            } else {
                if (this.getNestedValue(doc, key) !== value) return false;
            }
        }
        return true;
    }

    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => current?.[key], obj);
    }

    // Aggregate operations (simplified)
    async aggregate(collection, pipeline) {
        let results = Array.from(this.collections[collection].values());
        
        for (const stage of pipeline) {
            if (stage.$match) {
                results = results.filter(doc => this.matchesQuery(doc, stage.$match));
            } else if (stage.$group) {
                const grouped = {};
                const groupId = stage.$group._id;
                const accumulators = { ...stage.$group };
                delete accumulators._id;
                
                for (const doc of results) {
                    const key = groupId === null ? 'all' : this.getNestedValue(doc, groupId);
                    if (!grouped[key]) {
                        grouped[key] = { _id: key };
                        for (const [accField, accOp] of Object.entries(accumulators)) {
                            grouped[key][accField] = accOp.$sum ? 0 : accOp.$avg ? { sum: 0, count: 0 } : 0;
                        }
                    }
                    
                    for (const [accField, accOp] of Object.entries(accumulators)) {
                        if (accOp.$sum) {
                            grouped[key][accField] += accOp.$sum === 1 ? 1 : this.getNestedValue(doc, accOp.$sum);
                        } else if (accOp.$avg) {
                            const val = this.getNestedValue(doc, accOp.$avg);
                            grouped[key][accField].sum += val;
                            grouped[key][accField].count += 1;
                        }
                    }
                }
                
                // Convert avg accumulators to actual averages
                for (const group of Object.values(grouped)) {
                    for (const [accField, accOp] of Object.entries(accumulators)) {
                        if (accOp.$avg) {
                            group[accField] = group[accField].count > 0 ? group[accField].sum / group[accField].count : 0;
                        }
                    }
                }
                
                results = Object.values(grouped);
            } else if (stage.$sort) {
                results.sort((a, b) => {
                    for (const [field, direction] of Object.entries(stage.$sort)) {
                        const aVal = this.getNestedValue(a, field);
                        const bVal = this.getNestedValue(b, field);
                        if (aVal < bVal) return direction === 1 ? -1 : 1;
                        if (aVal > bVal) return direction === 1 ? 1 : -1;
                    }
                    return 0;
                });
            } else if (stage.$limit) {
                results = results.slice(0, stage.$limit);
            }
        }
        
        return results;
    }

    // Clear all data (for testing)
    clear() {
        this.collections.songs.clear();
        this.collections.userPreferences.clear();
        this.collections.musicInteractions.clear();
        this.counters = { songs: 0, userPreferences: 0, musicInteractions: 0 };
        console.log('🗑️  [TEMP_DB] All data cleared');
    }

    // Get collection stats
    getStats() {
        return {
            songs: this.collections.songs.size,
            userPreferences: this.collections.userPreferences.size,
            musicInteractions: this.collections.musicInteractions.size
        };
    }
}

// Create singleton instance
const tempDb = new TempDatabase();

module.exports = tempDb;
