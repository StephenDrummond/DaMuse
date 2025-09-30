// Channel configuration for the bot
const channelConfig = {
    // Default channels for different purposes
    music: {
        // Channel where music commands should be used
        allowed: ['music', 'bot-commands', 'general']
    },
    
    // Logging channels
    logs: {
        // Channel for bot logs
        general: 'bot-logs',
        music: 'music-logs'
    }
};

module.exports = channelConfig;

