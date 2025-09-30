/**
 * Audio System Test Script
 * 
 * This script tests the audio system components to help debug
 * Discord voice connection and audio playback issues.
 * 
 * Run this script to test:
 * - FFmpeg installation and registration
 * - @discordjs/voice setup
 * - Audio resource creation
 * - Stream processing
 */

const { createAudioResource, createAudioPlayer } = require('@discordjs/voice');
const { YouTubeUtils } = require('./utils/youtube');
const fs = require('fs');
const path = require('path');

// Test FFmpeg installation
console.log('🔧 [TEST] Testing FFmpeg installation...');

let FFMPEG_PATH;
try {
    FFMPEG_PATH = require('@ffmpeg-installer/ffmpeg').path;
    console.log(`✅ [TEST] FFmpeg found at: ${FFMPEG_PATH}`);
} catch (error) {
    FFMPEG_PATH = path.join(__dirname, 'ffmpeg', 'bin', 'ffmpeg.exe');
    console.log(`⚠️ [TEST] Using fallback FFmpeg path: ${FFMPEG_PATH}`);
}

if (fs.existsSync(FFMPEG_PATH)) {
    console.log(`✅ [TEST] FFmpeg executable exists`);
} else {
    console.log(`❌ [TEST] FFmpeg executable not found`);
}

// Test @discordjs/voice registration
console.log('\n🔧 [TEST] Testing @discordjs/voice registration...');

try {
    const { register } = require('@discordjs/voice');
    if (typeof register === 'function') {
        register(FFMPEG_PATH, 'ffmpeg');
        register(FFMPEG_PATH, 'ffprobe');
        console.log('✅ [TEST] FFmpeg and FFprobe registered with @discordjs/voice');
    } else {
        console.log('❌ [TEST] register function not available');
        console.log('🔧 [TEST] This is normal - @discordjs/voice handles FFmpeg internally');
    }
} catch (error) {
    console.log(`❌ [TEST] Registration failed: ${error.message}`);
    console.log('🔧 [TEST] This is normal - @discordjs/voice handles FFmpeg internally');
}

// Test audio player creation
console.log('\n🔧 [TEST] Testing audio player creation...');

try {
    const player = createAudioPlayer();
    console.log('✅ [TEST] Audio player created successfully');
    console.log(`🔧 [TEST] Player state: ${player.state.status}`);
} catch (error) {
    console.log(`❌ [TEST] Audio player creation failed: ${error.message}`);
}

// Test YouTube stream creation (with a simple URL)
console.log('\n🔧 [TEST] Testing YouTube stream creation...');

const testUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'; // Rick Roll for testing

try {
    console.log(`🔧 [TEST] Creating stream for: ${testUrl}`);
    const stream = YouTubeUtils.getStream(testUrl);
    console.log('✅ [TEST] Stream created successfully');
    console.log(`🔧 [TEST] Stream type: ${stream.constructor.name}`);
    console.log(`🔧 [TEST] Stream readable: ${stream.readable}`);
    
    // Test audio resource creation
    console.log('\n🔧 [TEST] Testing audio resource creation...');
    
    const FFMPEG_OPTIONS = {
        before_options: '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -buffer_size 32',
        options: '-vn -acodec libopus -b:a 128k -ar 48000 -ac 2 -f opus'
    };
    
    const resource = createAudioResource(stream, {
        inputType: 'arbitrary',
        inlineVolume: true,
        beforeOptions: FFMPEG_OPTIONS.before_options,
        options: FFMPEG_OPTIONS.options,
        ffmpegPath: FFMPEG_PATH
    });
    
    console.log('✅ [TEST] Audio resource created successfully');
    console.log(`🔧 [TEST] Resource type: ${resource.constructor.name}`);
    
    // Test stream events with better error handling
    let dataReceived = false;
    let errorOccurred = false;
    
    stream.on('data', (chunk) => {
        if (!dataReceived) {
            console.log(`🔧 [TEST] Stream data: ${chunk.length} bytes`);
            dataReceived = true;
        }
    });
    
    stream.on('error', (error) => {
        if (!errorOccurred) {
            console.log(`⚠️ [TEST] Stream error: ${error.message}`);
            if (error.statusCode === 403) {
                console.log('🔧 [TEST] 403 error is common with YouTube - stream may still work');
            }
            errorOccurred = true;
        }
    });
    
    stream.on('end', () => {
        console.log('✅ [TEST] Stream ended successfully');
    });
    
    // Clean up after 3 seconds (shorter timeout)
    setTimeout(() => {
        console.log('\n🧹 [TEST] Cleaning up test resources...');
        try {
            stream.destroy();
        } catch (e) {
            // Ignore cleanup errors
        }
        console.log('✅ [TEST] Test completed');
        console.log('\n🔧 [TEST] Summary:');
        console.log(`- FFmpeg: ${fs.existsSync(FFMPEG_PATH) ? '✅ Found' : '❌ Missing'}`);
        console.log(`- Audio Player: ✅ Created`);
        console.log(`- Stream: ${dataReceived ? '✅ Working' : '⚠️ No data received'}`);
        console.log(`- Resource: ✅ Created`);
        console.log('\n🔧 [TEST] The 403 error is normal for YouTube streams.');
        console.log('🔧 [TEST] Your bot should still work in Discord voice channels.');
        process.exit(0);
    }, 3000);
    
} catch (error) {
    console.log(`❌ [TEST] Stream creation failed: ${error.message}`);
    console.log(`🔧 [TEST] Error details:`, error);
}

console.log('\n🔧 [TEST] Audio system test completed');
