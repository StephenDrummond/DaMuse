FFmpeg 64-bit static Windows build from www.gyan.dev

Version: 2025-09-22-git-c9168717bf-essentials_build-www.gyan.dev

License: GPL v3

Source Code: https://github.com/FFmpeg/FFmpeg/commit/c9168717bf

git-essentials build configuration: 

ARCH                      x86 (generic)
big-endian                no
runtime cpu detection     yes
standalone assembly       yes
x86 assembler             nasm
MMX enabled               yes
MMXEXT enabled            yes
3DNow! enabled            yes
3DNow! extended enabled   yes
SSE enabled               yes
SSSE3 enabled             yes
AESNI enabled             yes
AVX enabled               yes
AVX2 enabled              yes
AVX-512 enabled           yes
AVX-512ICL enabled        yes
XOP enabled               yes
FMA3 enabled              yes
FMA4 enabled              yes
i686 features enabled     yes
CMOV is fast              yes
EBX available             yes
EBP available             yes
debug symbols             yes
strip symbols             yes
optimize for size         no
optimizations             yes
static                    yes
shared                    no
network support           yes
threading support         pthreads
safe bitstream reader     yes
texi2html enabled         no
perl enabled              yes
pod2man enabled           yes
makeinfo enabled          yes
makeinfo supports HTML    yes
experimental features     yes
xmllint enabled           yes

External libraries:
avisynth                libopencore_amrnb       libvpx
bzlib                   libopencore_amrwb       libwebp
gmp                     libopenjpeg             libx264
gnutls                  libopenmpt              libx265
iconv                   libopus                 libxml2
libaom                  librubberband           libxvid
libass                  libspeex                libzimg
libfontconfig           libsrt                  libzmq
libfreetype             libssh                  lzma
libfribidi              libtheora               mediafoundation
libgme                  libvidstab              openal
libgsm                  libvmaf                 sdl2
libharfbuzz             libvo_amrwbenc          zlib
libmp3lame              libvorbis

External libraries providing hardware acceleration:
amf                     d3d12va                 nvdec
cuda                    dxva2                   nvenc
cuda_llvm               ffnvcodec               vaapi
cuvid                   libmfx
d3d11va                 libvpl

Libraries:
avcodec                 avformat                swscale
avdevice                avutil
avfilter                swresample

Programs:
ffmpeg                  ffplay                  ffprobe

Enabled decoders:
aac                     fraps                   pgmyuv
aac_fixed               frwu                    pgssub
aac_latm                ftr                     pgx
aasc                    g2m                     phm
ac3                     g723_1                  photocd
ac3_fixed               g728                    pictor
acelp_kelvin            g729                    pixlet
adpcm_4xm               gdv                     pjs
adpcm_adx               gem                     png
adpcm_afc               gif                     ppm
adpcm_agm               gremlin_dpcm            prores
adpcm_aica              gsm                     prores_raw
adpcm_argo              gsm_ms                  prosumer
adpcm_ct                h261                    psd
adpcm_dtk               h263                    ptx
adpcm_ea                h263i                   qcelp
adpcm_ea_maxis_xa       h263p                   qdm2
adpcm_ea_r1             h264                    qdmc
adpcm_ea_r2             h264_amf                qdraw
adpcm_ea_r3             h264_cuvid              qoa
adpcm_ea_xas            h264_qsv                qoi
adpcm_g722              hap                     qpeg
adpcm_g726              hca                     qtrle
adpcm_g726le            hcom                    r10k
adpcm_ima_acorn         hdr                     r210
adpcm_ima_alp           hevc                    ra_144
adpcm_ima_amv           hevc_amf                ra_288
adpcm_ima_apc           hevc_cuvid              ralf
adpcm_ima_apm           hevc_qsv                rasc
adpcm_ima_cunning       hnm4_video              rawvideo
adpcm_ima_dat4          hq_hqa                  realtext
adpcm_ima_dk3           hqx                     rka
adpcm_ima_dk4           huffyuv                 rl2
adpcm_ima_ea_eacs       hymt                    roq
adpcm_ima_ea_sead       iac                     roq_dpcm
adpcm_ima_iss           idcin                   rpza
adpcm_ima_moflex        idf                     rscc
adpcm_ima_mtf           iff_ilbm                rtv1
adpcm_ima_oki           ilbc                    rv10
adpcm_ima_qt            imc                     rv20
adpcm_ima_rad           imm4                    rv30
adpcm_ima_smjpeg        imm5                    rv40
adpcm_ima_ssi           indeo2                  rv60
adpcm_ima_wav           indeo3                  s302m
adpcm_ima_ws            indeo4                  sami
adpcm_ima_xbox          indeo5                  sanm
adpcm_ms                interplay_acm           sbc
adpcm_mtaf              interplay_dpcm          scpr
adpcm_psx               interplay_video         screenpresso
adpcm_sanyo             ipu                     sdx2_dpcm
adpcm_sbpro_2           jacosub                 sga
adpcm_sbpro_3           jpeg2000                sgi
adpcm_sbpro_4           jpegls                  sgirle
adpcm_swf               jv                      sheervideo
adpcm_thp               kgv1                    shorten
adpcm_thp_le            kmvc                    simbiosis_imx
adpcm_vima              lagarith                sipr
adpcm_xa                lead                    siren
adpcm_xmd               libaom_av1              smackaud
adpcm_yamaha            libgsm                  smacker
adpcm_zork              libgsm_ms               smc
agm                     libopencore_amrnb       smvjpeg
aic                     libopencore_amrwb       snow
alac                    libopus                 sol_dpcm
alias_pix               libspeex                sonic
als                     libvorbis               sp5x
amrnb                   libvpx_vp8              speedhq
amrwb                   libvpx_vp9              speex
amv                     loco                    srgc
anm                     lscr                    srt
ansi                    m101                    ssa
anull                   mace3                   stl
apac                    mace6                   subrip
ape                     magicyuv                subviewer
apng                    mdec                    subviewer1
aptx                    media100                sunrast
aptx_hd                 metasound               svq1
apv                     microdvd                svq3
arbc                    mimic                   tak
argo                    misc4                   targa
ass                     mjpeg                   targa_y216
asv1                    mjpeg_cuvid             tdsc
asv2                    mjpeg_qsv               text
atrac1                  mjpegb                  theora
atrac3                  mlp                     thp
atrac3al                mmvideo                 tiertexseqvideo
atrac3p                 mobiclip                tiff
atrac3pal               motionpixels            tmv
atrac9                  movtext                 truehd
aura                    mp1                     truemotion1
aura2                   mp1float                truemotion2
av1                     mp2                     truemotion2rt
av1_amf                 mp2float                truespeech
av1_cuvid               mp3                     tscc
av1_qsv                 mp3adu                  tscc2
avrn                    mp3adufloat             tta
avrp                    mp3float                twinvq
avs                     mp3on4                  txd
avui                    mp3on4float             ulti
bethsoftvid             mpc7                    utvideo
bfi                     mpc8                    v210
bink                    mpeg1_cuvid             v210x
binkaudio_dct           mpeg1video              v308
binkaudio_rdft          mpeg2_cuvid             v408
bintext                 mpeg2_qsv               v410
bitpacked               mpeg2video              vb
bmp                     mpeg4                   vble
bmv_audio               mpeg4_cuvid             vbn
bmv_video               mpegvideo               vc1
bonk                    mpl2                    vc1_cuvid
brender_pix             msa1                    vc1_qsv
c93                     mscc                    vc1image
cavs                    msmpeg4v1               vcr1
cbd2_dpcm               msmpeg4v2               vmdaudio
ccaption                msmpeg4v3               vmdvideo
cdgraphics              msnsiren                vmix
cdtoons                 msp2                    vmnc
cdxl                    msrle                   vnull
cfhd                    mss1                    vorbis
cinepak                 mss2                    vp3
clearvideo              msvideo1                vp4
cljr                    mszh                    vp5
cllc                    mts2                    vp6
comfortnoise            mv30                    vp6a
cook                    mvc1                    vp6f
cpia                    mvc2                    vp7
cri                     mvdv                    vp8
cscd                    mvha                    vp8_cuvid
cyuv                    mwsc                    vp8_qsv
dca                     mxpeg                   vp9
dds                     nellymoser              vp9_amf
derf_dpcm               notchlc                 vp9_cuvid
dfa                     nuv                     vp9_qsv
dfpwm                   on2avc                  vplayer
dirac                   opus                    vqa
dnxhd                   osq                     vqc
dolby_e                 paf_audio               vvc
dpx                     paf_video               vvc_qsv
dsd_lsbf                pam                     wady_dpcm
dsd_lsbf_planar         pbm                     wavarc
dsd_msbf                pcm_alaw                wavpack
dsd_msbf_planar         pcm_bluray              wbmp
dsicinaudio             pcm_dvd                 wcmv
dsicinvideo             pcm_f16le               webp
dss_sp                  pcm_f24le               webvtt
dst                     pcm_f32be               wmalossless
dvaudio                 pcm_f32le               wmapro
dvbsub                  pcm_f64be               wmav1
dvdsub                  pcm_f64le               wmav2
dvvideo                 pcm_lxf                 wmavoice
dxa                     pcm_mulaw               wmv1
dxtory                  pcm_s16be               wmv2
dxv                     pcm_s16be_planar        wmv3
eac3                    pcm_s16le               wmv3image
eacmv                   pcm_s16le_planar        wnv1
eamad                   pcm_s24be               wrapped_avframe
eatgq                   pcm_s24daud             ws_snd1
eatgv                   pcm_s24le               xan_dpcm
eatqi                   pcm_s24le_planar        xan_wc3
eightbps                pcm_s32be               xan_wc4
eightsvx_exp            pcm_s32le               xbin
eightsvx_fib            pcm_s32le_planar        xbm
escape124               pcm_s64be               xface
escape130               pcm_s64le               xl
evrc                    pcm_s8                  xma1
exr                     pcm_s8_planar           xma2
fastaudio               pcm_sga                 xpm
ffv1                    pcm_u16be               xsub
ffvhuff                 pcm_u16le               xwd
ffwavesynth             pcm_u24be               y41p
fic                     pcm_u24le               ylc
fits                    pcm_u32be               yop
flac                    pcm_u32le               yuv4
flashsv                 pcm_u8                  zero12v
flashsv2                pcm_vidc                zerocodec
flic                    pcx                     zlib
flv                     pdv                     zmbv
fmvc                    pfm
fourxm                  pgm

Enabled encoders:
a64multi                hevc_d3d12va            pcm_u16le
a64multi5               hevc_mf                 pcm_u24be
aac                     hevc_nvenc              pcm_u24le
aac_mf                  hevc_qsv                pcm_u32be
ac3                     hevc_vaapi              pcm_u32le
ac3_fixed               huffyuv                 pcm_u8
ac3_mf                  jpeg2000                pcm_vidc
adpcm_adx               jpegls                  pcx
adpcm_argo              libaom_av1              pfm
adpcm_g722              libgsm                  pgm
adpcm_g726              libgsm_ms               pgmyuv
adpcm_g726le            libmp3lame              phm
adpcm_ima_alp           libopencore_amrnb       png
adpcm_ima_amv           libopenjpeg             ppm
adpcm_ima_apm           libopus                 prores
adpcm_ima_qt            libspeex                prores_aw
adpcm_ima_ssi           libtheora               prores_ks
adpcm_ima_wav           libvo_amrwbenc          qoi
adpcm_ima_ws            libvorbis               qtrle
adpcm_ms                libvpx_vp8              r10k
adpcm_swf               libvpx_vp9              r210
adpcm_yamaha            libwebp                 ra_144
alac                    libwebp_anim            rawvideo
alias_pix               libx264                 roq
amv                     libx264rgb              roq_dpcm
anull                   libx265                 rpza
apng                    libxvid                 rv10
aptx                    ljpeg                   rv20
aptx_hd                 magicyuv                s302m
ass                     mjpeg                   sbc
asv1                    mjpeg_qsv               sgi
asv2                    mjpeg_vaapi             smc
av1_amf                 mlp                     snow
av1_mf                  movtext                 speedhq
av1_nvenc               mp2                     srt
av1_qsv                 mp2fixed                ssa
av1_vaapi               mp3_mf                  subrip
avrp                    mpeg1video              sunrast
avui                    mpeg2_qsv               svq1
bitpacked               mpeg2_vaapi             targa
bmp                     mpeg2video              text
cfhd                    mpeg4                   tiff
cinepak                 msmpeg4v2               truehd
cljr                    msmpeg4v3               tta
comfortnoise            msrle                   ttml
dca                     msvideo1                utvideo
dfpwm                   nellymoser              v210
dnxhd                   opus                    v308
dpx                     pam                     v408
dvbsub                  pbm                     v410
dvdsub                  pcm_alaw                vbn
dvvideo                 pcm_bluray              vc2
dxv                     pcm_dvd                 vnull
eac3                    pcm_f32be               vorbis
exr                     pcm_f32le               vp8_vaapi
ffv1                    pcm_f64be               vp9_qsv
ffvhuff                 pcm_f64le               vp9_vaapi
fits                    pcm_mulaw               wavpack
flac                    pcm_s16be               wbmp
flashsv                 pcm_s16be_planar        webvtt
flashsv2                pcm_s16le               wmav1
flv                     pcm_s16le_planar        wmav2
g723_1                  pcm_s24be               wmv1
gif                     pcm_s24daud             wmv2
h261                    pcm_s24le               wrapped_avframe
h263                    pcm_s24le_planar        xbm
h263p                   pcm_s32be               xface
h264_amf                pcm_s32le               xsub
h264_mf                 pcm_s32le_planar        xwd
h264_nvenc              pcm_s64be               y41p
h264_qsv                pcm_s64le               yuv4
h264_vaapi              pcm_s8                  zlib
hdr                     pcm_s8_planar           zmbv
hevc_amf                pcm_u16be

Enabled hwaccels:
av1_d3d11va             hevc_nvdec              vc1_nvdec
av1_d3d11va2            hevc_vaapi              vc1_vaapi
av1_d3d12va             mjpeg_nvdec             vp8_nvdec
av1_dxva2               mjpeg_vaapi             vp8_vaapi
av1_nvdec               mpeg1_nvdec             vp9_d3d11va
av1_vaapi               mpeg2_d3d11va           vp9_d3d11va2
h263_vaapi              mpeg2_d3d11va2          vp9_d3d12va
h264_d3d11va            mpeg2_d3d12va           vp9_dxva2
h264_d3d11va2           mpeg2_dxva2             vp9_nvdec
h264_d3d12va            mpeg2_nvdec             vp9_vaapi
h264_dxva2              mpeg2_vaapi             vvc_vaapi
h264_nvdec              mpeg4_nvdec             wmv3_d3d11va
h264_vaapi              mpeg4_vaapi             wmv3_d3d11va2
hevc_d3d11va            vc1_d3d11va             wmv3_d3d12va
hevc_d3d11va2           vc1_d3d11va2            wmv3_dxva2
hevc_d3d12va            vc1_d3d12va             wmv3_nvdec
hevc_dxva2              vc1_dxva2               wmv3_vaapi

Enabled parsers:
aac                     dvdsub                  mpegvideo
aac_latm                evc                     opus
ac3                     ffv1                    png
adx                     flac                    pnm
amr                     ftr                     prores_raw
apv                     g723_1                  qoi
av1                     g729                    rv34
avs2                    gif                     sbc
avs3                    gsm                     sipr
bmp                     h261                    tak
cavsvideo               h263                    vc1
cook                    h264                    vorbis
cri                     hdr                     vp3
dca                     hevc                    vp8
dirac                   ipu                     vp9
dnxhd                   jpeg2000                vvc
dnxuc                   jpegxl                  webp
dolby_e                 misc4                   xbm
dpx                     mjpeg                   xma
dvaudio                 mlp                     xwd
dvbsub                  mpeg4video
dvd_nav                 mpegaudio

Enabled demuxers:
aa                      ico                     pcm_f64le
aac                     idcin                   pcm_mulaw
aax                     idf                     pcm_s16be
ac3                     iff                     pcm_s16le
ac4                     ifv                     pcm_s24be
ace                     ilbc                    pcm_s24le
acm                     image2                  pcm_s32be
act                     image2_alias_pix        pcm_s32le
adf                     image2_brender_pix      pcm_s8
adp                     image2pipe              pcm_u16be
ads                     image_bmp_pipe          pcm_u16le
adx                     image_cri_pipe          pcm_u24be
aea                     image_dds_pipe          pcm_u24le
afc                     image_dpx_pipe          pcm_u32be
aiff                    image_exr_pipe          pcm_u32le
aix                     image_gem_pipe          pcm_u8
alp                     image_gif_pipe          pcm_vidc
amr                     image_hdr_pipe          pdv
amrnb                   image_j2k_pipe          pjs
amrwb                   image_jpeg_pipe         pmp
anm                     image_jpegls_pipe       pp_bnk
apac                    image_jpegxl_pipe       pva
apc                     image_pam_pipe          pvf
ape                     image_pbm_pipe          qcp
apm                     image_pcx_pipe          qoa
apng                    image_pfm_pipe          r3d
aptx                    image_pgm_pipe          rawvideo
aptx_hd                 image_pgmyuv_pipe       rcwt
apv                     image_pgx_pipe          realtext
aqtitle                 image_phm_pipe          redspark
argo_asf                image_photocd_pipe      rka
argo_brp                image_pictor_pipe       rl2
argo_cvg                image_png_pipe          rm
asf                     image_ppm_pipe          roq
asf_o                   image_psd_pipe          rpl
ass                     image_qdraw_pipe        rsd
ast                     image_qoi_pipe          rso
au                      image_sgi_pipe          rtp
av1                     image_sunrast_pipe      rtsp
avi                     image_svg_pipe          s337m
avisynth                image_tiff_pipe         sami
avr                     image_vbn_pipe          sap
avs                     image_webp_pipe         sbc
avs2                    image_xbm_pipe          sbg
avs3                    image_xpm_pipe          scc
bethsoftvid             image_xwd_pipe          scd
bfi                     imf                     sdns
bfstm                   ingenient               sdp
bink                    ipmovie                 sdr2
binka                   ipu                     sds
bintext                 ircam                   sdx
bit                     iss                     segafilm
bitpacked               iv8                     ser
bmv                     ivf                     sga
boa                     ivr                     shorten
bonk                    jacosub                 siff
brstm                   jpegxl_anim             simbiosis_imx
c93                     jv                      sln
caf                     kux                     smacker
cavsvideo               kvag                    smjpeg
cdg                     laf                     smush
cdxl                    lc3                     sol
cine                    libgme                  sox
codec2                  libopenmpt              spdif
codec2raw               live_flv                srt
concat                  lmlm4                   stl
dash                    loas                    str
data                    lrc                     subviewer
daud                    luodat                  subviewer1
dcstr                   lvf                     sup
derf                    lxf                     svag
dfa                     m4v                     svs
dfpwm                   matroska                swf
dhav                    mca                     tak
dirac                   mcc                     tedcaptions
dnxhd                   mgsts                   thp
dsf                     microdvd                threedostr
dsicin                  mjpeg                   tiertexseq
dss                     mjpeg_2000              tmv
dts                     mlp                     truehd
dtshd                   mlv                     tta
dv                      mm                      tty
dvbsub                  mmf                     txd
dvbtxt                  mods                    ty
dxa                     moflex                  usm
ea                      mov                     v210
ea_cdata                mp3                     v210x
eac3                    mpc                     vag
epaf                    mpc8                    vc1
evc                     mpegps                  vc1t
ffmetadata              mpegts                  vividas
filmstrip               mpegtsraw               vivo
fits                    mpegvideo               vmd
flac                    mpjpeg                  vobsub
flic                    mpl2                    voc
flv                     mpsub                   vpk
fourxm                  msf                     vplayer
frm                     msnwc_tcp               vqf
fsb                     msp                     vvc
fwse                    mtaf                    w64
g722                    mtv                     wady
g723_1                  musx                    wav
g726                    mv                      wavarc
g726le                  mvi                     wc3
g728                    mxf                     webm_dash_manifest
g729                    mxg                     webvtt
gdv                     nc                      wsaud
genh                    nistsphere              wsd
gif                     nsp                     wsvqa
gsm                     nsv                     wtv
gxf                     nut                     wv
h261                    nuv                     wve
h263                    obu                     xa
h264                    ogg                     xbin
hca                     oma                     xmd
hcom                    osq                     xmv
hevc                    paf                     xvag
hls                     pcm_alaw                xwma
hnm                     pcm_f32be               yop
hxvs                    pcm_f32le               yuv4mpegpipe
iamf                    pcm_f64be

Enabled muxers:
a64                     h263                    pcm_s16le
ac3                     h264                    pcm_s24be
ac4                     hash                    pcm_s24le
adts                    hds                     pcm_s32be
adx                     hevc                    pcm_s32le
aea                     hls                     pcm_s8
aiff                    iamf                    pcm_u16be
alp                     ico                     pcm_u16le
amr                     ilbc                    pcm_u24be
amv                     image2                  pcm_u24le
apm                     image2pipe              pcm_u32be
apng                    ipod                    pcm_u32le
aptx                    ircam                   pcm_u8
aptx_hd                 ismv                    pcm_vidc
apv                     ivf                     psp
argo_asf                jacosub                 rawvideo
argo_cvg                kvag                    rcwt
asf                     latm                    rm
asf_stream              lc3                     roq
ass                     lrc                     rso
ast                     m4v                     rtp
au                      matroska                rtp_mpegts
avi                     matroska_audio          rtsp
avif                    mcc                     sap
avm2                    md5                     sbc
avs2                    microdvd                scc
avs3                    mjpeg                   segafilm
bit                     mkvtimestamp_v2         segment
caf                     mlp                     smjpeg
cavsvideo               mmf                     smoothstreaming
codec2                  mov                     sox
codec2raw               mp2                     spdif
crc                     mp3                     spx
dash                    mp4                     srt
data                    mpeg1system             stream_segment
daud                    mpeg1vcd                streamhash
dfpwm                   mpeg1video              sup
dirac                   mpeg2dvd                swf
dnxhd                   mpeg2svcd               tee
dts                     mpeg2video              tg2
dv                      mpeg2vob                tgp
eac3                    mpegts                  truehd
evc                     mpjpeg                  tta
f4v                     mxf                     ttml
ffmetadata              mxf_d10                 uncodedframecrc
fifo                    mxf_opatom              vc1
filmstrip               null                    vc1t
fits                    nut                     voc
flac                    obu                     vvc
flv                     oga                     w64
framecrc                ogg                     wav
framehash               ogv                     webm
framemd5                oma                     webm_chunk
g722                    opus                    webm_dash_manifest
g723_1                  pcm_alaw                webp
g726                    pcm_f32be               webvtt
g726le                  pcm_f32le               wsaud
gif                     pcm_f64be               wtv
gsm                     pcm_f64le               wv
gxf                     pcm_mulaw               yuv4mpegpipe
h261                    pcm_s16be

Enabled protocols:
async                   http                    rtmp
cache                   httpproxy               rtmpe
concat                  https                   rtmps
concatf                 icecast                 rtmpt
crypto                  ipfs_gateway            rtmpte
data                    ipns_gateway            rtmpts
fd                      libsrt                  rtp
ffrtmpcrypt             libssh                  srtp
ffrtmphttp              libzmq                  subfile
file                    md5                     tcp
ftp                     mmsh                    tee
gopher                  mmst                    tls
gophers                 pipe                    udp
hls                     prompeg                 udplite

Enabled filters:
a3dscope                datascope               paletteuse
aap                     dblur                   pan
abench                  dcshift                 perlin
abitscope               dctdnoiz                perms
acompressor             ddagrab                 perspective
acontrast               deband                  phase
acopy                   deblock                 photosensitivity
acrossfade              decimate                pixdesctest
acrossover              deconvolve              pixelize
acrusher                dedot                   pixscope
acue                    deesser                 pp7
addroi                  deflate                 premultiply
adeclick                deflicker               premultiply_dynamic
adeclip                 deinterlace_qsv         prewitt
adecorrelate            deinterlace_vaapi       procamp_vaapi
adelay                  dejudder                pseudocolor
adenorm                 delogo                  psnr
aderivative             denoise_vaapi           pullup
adrawgraph              deshake                 qp
adrc                    despill                 random
adynamicequalizer       detelecine              readeia608
adynamicsmooth          dialoguenhance          readvitc
aecho                   dilation                realtime
aemphasis               displace                remap
aeval                   doubleweave             removegrain
aevalsrc                drawbox                 removelogo
aexciter                drawbox_vaapi           repeatfields
afade                   drawgraph               replaygain
afdelaysrc              drawgrid                reverse
afftdn                  drawtext                rgbashift
afftfilt                drmeter                 rgbtestsrc
afir                    dynaudnorm              roberts
afireqsrc               earwax                  rotate
afirsrc                 ebur128                 rubberband
aformat                 edgedetect              sab
afreqshift              elbg                    scale
afwtdn                  entropy                 scale2ref
agate                   epx                     scale_cuda
agraphmonitor           eq                      scale_d3d11
ahistogram              equalizer               scale_qsv
aiir                    erosion                 scale_vaapi
aintegral               estdif                  scdet
ainterleave             exposure                scharr
alatency                extractplanes           scroll
alimiter                extrastereo             segment
allpass                 fade                    select
allrgb                  feedback                selectivecolor
allyuv                  fftdnoiz                sendcmd
aloop                   fftfilt                 separatefields
alphaextract            field                   setdar
alphamerge              fieldhint               setfield
amerge                  fieldmatch              setparams
ametadata               fieldorder              setpts
amix                    fillborders             setrange
amovie                  find_rect               setsar
amplify                 firequalizer            settb
amultiply               flanger                 sharpness_vaapi
anequalizer             floodfill               shear
anlmdn                  format                  showcqt
anlmf                   fps                     showcwt
anlms                   framepack               showfreqs
anoisesrc               framerate               showinfo
anull                   framestep               showpalette
anullsink               freezedetect            showspatial
anullsrc                freezeframes            showspectrum
apad                    fspp                    showspectrumpic
aperms                  fsync                   showvolume
aphasemeter             gblur                   showwaves
aphaser                 geq                     showwavespic
aphaseshift             gfxcapture              shuffleframes
apsnr                   gradfun                 shufflepixels
apsyclip                gradients               shuffleplanes
apulsator               graphmonitor            sidechaincompress
arealtime               grayworld               sidechaingate
aresample               greyedge                sidedata
areverse                guided                  sierpinski
arls                    haas                    signalstats
arnndn                  haldclut                signature
asdr                    haldclutsrc             silencedetect
asegment                hdcd                    silenceremove
aselect                 headphone               sinc
asendcmd                hflip                   sine
asetnsamples            highpass                siti
asetpts                 highshelf               smartblur
asetrate                hilbert                 smptebars
asettb                  histeq                  smptehdbars
ashowinfo               histogram               sobel
asidedata               hqdn3d                  spectrumsynth
asisdr                  hqx                     speechnorm
asoftclip               hstack                  split
aspectralstats          hstack_qsv              spp
asplit                  hstack_vaapi            sr_amf
ass                     hsvhold                 ssim
astats                  hsvkey                  ssim360
astreamselect           hue                     stereo3d
asubboost               huesaturation           stereotools
asubcut                 hwdownload              stereowiden
asupercut               hwmap                   streamselect
asuperpass              hwupload                subtitles
asuperstop              hwupload_cuda           super2xsai
atadenoise              hysteresis              superequalizer
atempo                  identity                surround
atilt                   idet                    swaprect
atrim                   il                      swapuv
avectorscope            inflate                 tblend
avgblur                 interlace               telecine
avsynctest              interleave              testsrc
axcorrelate             join                    testsrc2
azmq                    kerndeint               thistogram
backgroundkey           kirsch                  threshold
bandpass                lagfun                  thumbnail
bandreject              latency                 thumbnail_cuda
bass                    lenscorrection          tile
bbox                    libvmaf                 tiltandshift
bench                   life                    tiltshelf
bilateral               limitdiff               tinterlace
bilateral_cuda          limiter                 tlut2
biquad                  loop                    tmedian
bitplanenoise           loudnorm                tmidequalizer
blackdetect             lowpass                 tmix
blackframe              lowshelf                tonemap
blend                   lumakey                 tonemap_vaapi
blockdetect             lut                     tpad
blurdetect              lut1d                   transpose
bm3d                    lut2                    transpose_vaapi
boxblur                 lut3d                   treble
bwdif                   lutrgb                  tremolo
bwdif_cuda              lutyuv                  trim
cas                     mandelbrot              unpremultiply
ccrepack                maskedclamp             unsharp
cellauto                maskedmax               untile
channelmap              maskedmerge             uspp
channelsplit            maskedmin               v360
chorus                  maskedthreshold         vaguedenoiser
chromahold              maskfun                 varblur
chromakey               mcdeint                 vectorscope
chromakey_cuda          mcompand                vflip
chromanr                median                  vfrdet
chromashift             mergeplanes             vibrance
ciescope                mestimate               vibrato
codecview               metadata                vidstabdetect
color                   midequalizer            vidstabtransform
colorbalance            minterpolate            vif
colorchannelmixer       mix                     vignette
colorchart              monochrome              virtualbass
colorcontrast           morpho                  vmafmotion
colorcorrect            movie                   volume
colordetect             mpdecimate              volumedetect
colorhold               mptestsrc               vpp_amf
colorize                msad                    vpp_qsv
colorkey                multiply                vstack
colorlevels             negate                  vstack_qsv
colormap                nlmeans                 vstack_vaapi
colormatrix             nnedi                   w3fdif
colorspace              noformat                waveform
colorspace_cuda         noise                   weave
colorspectrum           normalize               xbr
colortemperature        null                    xcorrelate
compand                 nullsink                xfade
compensationdelay       nullsrc                 xmedian
concat                  oscilloscope            xpsnr
convolution             overlay                 xstack
convolve                overlay_cuda            xstack_qsv
copy                    overlay_qsv             xstack_vaapi
corr                    overlay_vaapi           yadif
cover_rect              owdenoise               yadif_cuda
crop                    pad                     yaepblur
cropdetect              pad_cuda                yuvtestsrc
crossfeed               pad_vaapi               zmq
crystalizer             pal100bars              zoneplate
cue                     pal75bars               zoompan
curves                  palettegen              zscale

Enabled bsfs:
aac_adtstoasc           h264_metadata           pcm_rechunk
apv_metadata            h264_mp4toannexb        pgs_frame_merge
av1_frame_merge         h264_redundant_pps      prores_metadata
av1_frame_split         hapqa_extract           remove_extradata
av1_metadata            hevc_metadata           setts
chomp                   hevc_mp4toannexb        showinfo
dca_core                imx_dump_header         smpte436m_to_eia608
dovi_rpu                media100_to_mjpegb      text2movsub
dts2pts                 mjpeg2jpeg              trace_headers
dump_extradata          mjpega_dump_header      truehd_core
dv_error_marker         mov2textsub             vp9_metadata
eac3_core               mpeg2_metadata          vp9_raw_reorder
eia608_to_smpte436m     mpeg4_unpack_bframes    vp9_superframe
evc_frame_merge         noise                   vp9_superframe_split
extract_extradata       null                    vvc_metadata
filter_units            opus_metadata           vvc_mp4toannexb

Enabled indevs:
dshow                   lavfi                   vfwcap
gdigrab                 openal

Enabled outdevs:

git-essentials external libraries' versions: 

AMF v1.4.36-4-g5e3b7df
aom v3.13.1-50-gd459fa9018
AviSynthPlus v3.7.5-32-g805fda74
ffnvcodec n13.0.19.0-2-g876af32
freetype VER-2-14-1
fribidi v1.0.16-2-gb28f43b
gsm 1.0.22
harfbuzz 11.5.0-77-gfa7b7fd8
lame 3.100
libass 0.17.4-15-g534a5f8
libgme 0.6.4
libopencore-amrnb 0.1.6
libopencore-amrwb 0.1.6
libssh 0.11.2
libtheora v1.2.0
libwebp v1.6.0-96-gaae8a3d
openal-soft latest
openmpt libopenmpt-0.6.25-2-g55166e75b
opus v1.5.2-213-gb5dc74f2
rubberband v1.8.1
SDL release-2.32.0-108-gecb72142f
speex Speex-1.2.1-51-g0589522
srt v1.5.5-rc.0a
VAAPI 2.23.0.
vidstab v1.1.1-20-g4bd81e3
vmaf v3.0.0-113-g2b2cf9c1
vo-amrwbenc 0.1.3
vorbis v1.3.7-20-g43bbff01
VPL 2.15
vpx v1.15.2-119-g81afb68e7
x264 v0.165.3223
x265 4.1-191-g8f11c33ac
xvid v1.3.7
zeromq 4.3.5
zimg release-3.0.6-211-gdf9c147

