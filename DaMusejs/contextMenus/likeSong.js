// ⚠️  TEMPORARY: Using in-memory database models for testing
const { ContextMenuCommandBuilder, ApplicationCommandType, EmbedBuilder } = require('discord.js');
const { BaseCommand } = require('../utils/commandTemplate');
const { createValidationError } = require('../utils/errorHandler');
const Song = require('../models/tempSong');
const UserPreference = require('../models/tempUserPreference');
const MusicInteraction = require('../models/tempMusicInteraction');

class LikeSongCommand extends BaseCommand {
    constructor() {
        super(
            new ContextMenuCommandBuilder()
                .setName('Like Song')
                .setType(ApplicationCommandType.Message)
        );
    }

    async validateInput(interaction) {
        // Check if the message is from the bot (music bot messages)
        if (!interaction.targetMessage.author.bot) {
            throw createValidationError('You can only like songs that are currently playing!');
        }

        // Check if the message contains music information
        const content = interaction.targetMessage.content;
        const embeds = interaction.targetMessage.embeds;
        
        if (!content.includes('Now playing') && !content.includes('Song Queued') && 
            !embeds.some(embed => embed.title?.includes('🎵'))) {
            throw createValidationError('This message doesn\'t appear to be a music-related message!');
        }

        return {};
    }

    async executeCommand(interaction) {
        const { } = await this.validateInput(interaction);

        try {
            // Extract song information from the message
            const songInfo = this.extractSongInfo(interaction.targetMessage);
            
            if (!songInfo) {
                throw createValidationError('Could not extract song information from this message.');
            }

            // Find or create the song in the database
            const song = await Song.findOrCreate({
                title: songInfo.title,
                artist: songInfo.artist || 'Unknown Artist',
                url: songInfo.url,
                thumbnail: songInfo.thumbnail,
                duration: songInfo.duration || 0,
                genre: songInfo.genre || 'Unknown',
                mood: songInfo.mood || 'Neutral',
                energy: songInfo.energy || 5
            });

            // Record the like interaction
            await song.recordInteraction('like');
            
            // Update user preferences
            const userPref = await UserPreference.findOrCreate(
                interaction.user.id, 
                interaction.guild.id
            );
            await userPref.recordInteraction(song, 'like');

            // Record the interaction
            await MusicInteraction.recordInteraction({
                userId: interaction.user.id,
                guildId: interaction.guild.id,
                songId: song._id,
                interactionType: 'like'
            });

            return { 
                message: `👍 You liked **${song.title}** by ${song.artist}!`,
                song: song
            };

        } catch (error) {
            console.error('Error in like command:', error);
            throw createValidationError('Failed to like the song. Please try again.');
        }
    }

    async sendResponse(interaction, result) {
        const embed = new EmbedBuilder()
            .setTitle('👍 Song Liked!')
            .setDescription(result.message)
            .setColor(0x00ff00)
            .setThumbnail(result.song.thumbnail);

        await interaction.reply({ 
            embeds: [embed],
            flags: 64 
        });
    }

    extractSongInfo(message) {
        try {
            // Try to extract from embeds first
            if (message.embeds.length > 0) {
                const embed = message.embeds[0];
                const title = embed.title || '';
                const description = embed.description || '';
                
                if (title.includes('🎵')) {
                    return {
                        title: this.extractTitleFromText(description),
                        artist: this.extractArtistFromText(description),
                        url: embed.url || null,
                        thumbnail: embed.thumbnail?.url || null,
                        duration: this.extractDurationFromText(description)
                    };
                }
            }

            // Try to extract from message content
            const content = message.content;
            if (content.includes('Now playing') || content.includes('Song Queued')) {
                return {
                    title: this.extractTitleFromText(content),
                    artist: this.extractArtistFromText(content),
                    url: this.extractUrlFromText(content),
                    thumbnail: null,
                    duration: this.extractDurationFromText(content)
                };
            }

            return null;
        } catch (error) {
            console.error('Error extracting song info:', error);
            return null;
        }
    }

    extractTitleFromText(text) {
        // Look for patterns like "**Song Title**" or "Song Title"
        const titleMatch = text.match(/\*\*(.*?)\*\*/);
        if (titleMatch) {
            return titleMatch[1];
        }
        
        // Fallback: look for text after "Now playing:" or "Song Queued:"
        const playingMatch = text.match(/(?:Now playing|Song Queued):\s*(.+?)(?:\n|$)/);
        if (playingMatch) {
            return playingMatch[1].trim();
        }
        
        return 'Unknown Title';
    }

    extractArtistFromText(text) {
        // Look for "by Artist" pattern
        const artistMatch = text.match(/by\s+(.+?)(?:\n|$)/);
        if (artistMatch) {
            return artistMatch[1].trim();
        }
        
        return 'Unknown Artist';
    }

    extractUrlFromText(text) {
        // Look for YouTube URLs
        const urlMatch = text.match(/(https?:\/\/[^\s]+)/);
        return urlMatch ? urlMatch[1] : null;
    }

    extractDurationFromText(text) {
        // Look for duration patterns like "(3:45)" or "3:45"
        const durationMatch = text.match(/\((\d+:\d+)\)|(\d+:\d+)/);
        if (durationMatch) {
            const timeStr = durationMatch[1] || durationMatch[2];
            const [minutes, seconds] = timeStr.split(':').map(Number);
            return (minutes * 60 + seconds) * 1000; // Convert to milliseconds
        }
        
        return 0;
    }
}

module.exports = new LikeSongCommand();
