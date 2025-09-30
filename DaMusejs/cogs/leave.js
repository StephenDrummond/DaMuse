/**
 * Leave Command - Force Bot to Leave Voice Channel
 * 
 * This command forces the bot to leave the voice channel and clean up
 * all connections. Useful when the bot gets stuck in a voice channel.
 * 
 * @author DaMuse Team
 * @version 1.0.0
 */

const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { getVoiceConnection, joinVoiceChannel } = require('@discordjs/voice');
const { BaseCommand } = require('../utils/commandTemplate');
const { queues } = require('../music_state/queues');

/**
 * Leave Command Class
 * 
 * Forces the bot to leave the voice channel and clean up all connections.
 */
class LeaveCommand extends BaseCommand {
    constructor() {
        super(
            new SlashCommandBuilder()
                .setName('leave')
                .setDescription('Force the bot to leave the voice channel')
        );
    }

    async executeCommand(interaction) {
        const guildId = interaction.guild.id;
        const guild = interaction.guild;
        
        try {
            console.log(`🚪 [LEAVE] Forcing bot to leave voice channel for guild ${guildId}`);
            
            // Get existing connection
            const connection = getVoiceConnection(guildId);
            
            if (connection) {
                console.log(`🚪 [LEAVE] Found existing connection, destroying...`);
                connection.destroy();
                console.log(`🚪 [LEAVE] ✅ Connection destroyed`);
            } else {
                console.log(`🚪 [LEAVE] No existing connection object found. Checking voice state.`);
                // If no connection object, check if the bot is actually in a channel
                const member = guild.members.cache.get(interaction.client.user.id);
                if (member?.voice.channel) {
                    console.log(`🚪 [LEAVE] Bot is in a voice channel. Forcing disconnect.`);
                    // Force join and destroy to clear state
                    const tempConnection = joinVoiceChannel({
                        channelId: member.voice.channel.id,
                        guildId: guildId,
                        adapterCreator: guild.voiceAdapterCreator,
                    });
                    tempConnection.destroy();
                    console.log(`🚪 [LEAVE] ✅ Forcibly disconnected.`);
                } else {
                    console.log(`🚪 [LEAVE] Bot is not in a voice channel.`);
                }
            }
            
            // Clean up queue system
            queues.cleanupConnection(guildId);
            console.log(`🚪 [LEAVE] ✅ Queue system cleaned up`);
            
            // Create success embed
            const embed = new EmbedBuilder()
                .setTitle('🚪 Left Voice Channel')
                .setDescription('Bot has left the voice channel and cleaned up all connections.')
                .setColor(0x00ff00);
            
            await interaction.reply({ embeds: [embed] });
            console.log(`🚪 [LEAVE] ✅ Successfully left voice channel for guild ${guildId}`);
            
        } catch (error) {
            console.error(`🚪 [LEAVE] ❌ Error leaving voice channel:`, error);
            
            // Try to clean up anyway
            try {
                queues.cleanupConnection(guildId);
            } catch (cleanupError) {
                console.error(`🚪 [LEAVE] ❌ Cleanup also failed:`, cleanupError);
            }
            
            await interaction.reply('❌ Error leaving voice channel, but attempted cleanup.');
        }
    }
}

module.exports = new LeaveCommand();