# -*- coding: utf-8 -*-
# Module: MPD PARSER
# Created on: 27-10-2023
# Authors: TANZ
# Version: 1.0

import requests, xmltodict, isodate, re, os, json

os.system('')
BLACK = '\033[30m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'
UNDERLINE = '\033[4m'
RESET = '\033[0m'

mpd_url = input(f"{CYAN}\nEnter Your MPD URL: {RESET}")

def convert_size(size_bytes):
    if size_bytes == 0:
        return '0 bps'
    else:
        s = round(size_bytes / 1000, 0)
        return '%i kbps' % s

def get_size(size):
    power = 1024
    n = 0
    Dic_powerN = {0:' ',  1:' K',  2:' M',  3:' G',  4:' T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + Dic_powerN[n] + 'iB'

def parse_mpd(mpd_url):
    r = requests.get(url=mpd_url)
    if r.status_code == 403:
        print(f"{RED}{r}{RESET}")
    else:
        print(f"{GREEN}{r}{RESET}")
    if r.status_code != 200:
        exit()
    mpd = xmltodict.parse(r.text)
    tracks = mpd['MPD']['Period']['AdaptationSet']
    duration = isodate.parse_duration(mpd['MPD']['@mediaPresentationDuration']).total_seconds()

    mpd_content = r.text
    pattern_pssh = r'<cenc:pssh[^>]*>(.*?)</cenc:pssh>'
    search_pssh = re.search(pattern_pssh, mpd_content, re.DOTALL)
    pssh = search_pssh.group(1)

    def get_framerate(framerate_value):
        try:
            if '/' in framerate_value:
                numerator, denominator = map(int, framerate_value.split('/'))
                frame_rate = numerator / denominator
                return round(frame_rate, 3)
            else:
                return int(framerate_value)
        except (ValueError, ZeroDivisionError):
            return int(framerate_value)

    video_list = []
    for video_tracks in tracks:
        if video_tracks['@mimeType'] == 'video/mp4':
            representations = video_tracks.get('Representation', [])

            if isinstance(representations, list):
                for x in representations:
                    video_list.append({
                        'Height': x.get('@height', ''),
                        'Width': x.get('@width', ''),
                        'Bandwidth': x.get('@bandwidth', ''),
                        'FrameRate': get_framerate(x.get('@frameRate', '')),
                        'ID': x.get('@id', ''),
                        'Codec': x.get('@codecs', ''),
                    })
            elif isinstance(representations, dict):
                video_list.append({
                    'Height': representations.get('@height', ''),
                    'Width': representations.get('@width', ''),
                    'Bandwidth': representations.get('@bandwidth', ''),
                    'FrameRate': get_framerate(representations.get('@frameRate', '')),
                    'ID': representations.get('@id', ''),
                    'Codec': representations.get('@codecs', ''),
                })

    video_list = sorted(video_list, key=(lambda k: int(k['Bandwidth'])))

    audio_list = []
    for audio_tracks in tracks:
        if audio_tracks['@mimeType'] == 'audio/mp4':
            representations = audio_tracks.get('Representation', [])
            if isinstance(representations, list):
                for representation_dict in representations:
                    codecs = 'AAC' if 'mp4a' in representation_dict['@codecs'] else representation_dict['@codecs']
                    channels = '2.0' if codecs == 'AAC' else '5.1'
                    audio_list.append({
                        'Bandwidth': int(representation_dict.get('@bandwidth', 0)),
                        'ID': representation_dict.get('@id', ''),
                        'Codec': codecs,
                        'Channels': channels,
                    })
            elif isinstance(representations, dict):
                codecs = 'AAC' if 'mp4a' in representations['@codecs'] else representations['@codecs']
                channels = '2.0' if codecs == 'AAC' else '5.1'
                audio_list.append({
                    'Bandwidth': int(representations.get('@bandwidth', 0)),
                    'ID': representations.get('@id', ''),
                    'Codec': codecs,
                    'Channels': channels,
                })

    audio_list = sorted(audio_list, key=lambda k: k['Bandwidth'], reverse=True)

    subs_list = []
    for subtitle_tracks in tracks:
        if subtitle_tracks['@mimeType'] == 'text/vtt':
            representations = subtitle_tracks.get('Representation', [])
            if isinstance(representations, list):
                for representation_dict in representations:
                    subs_list.append({
                        'ID': representation_dict.get('@id', ''),
                        'Language': representation_dict.get('@id', '').split('/')[-1],
                        'Format': representation_dict.get('BaseURL', '').split('.')[-1],
                    })
            elif isinstance(representations, dict):
                subs_list.append({
                    'ID': representations.get('@id', ''),
                    'Language': representations.get('@id', '').split('/')[-1],
                    'Format': representations.get('BaseURL', '').split('.')[-1],
                })

    subs_list = sorted(subs_list, key=(lambda k: (str(k['ID']))))

    print(f"{YELLOW}\n[+] PSSH  - {RESET}{CYAN}{pssh}{RESET}\n")

    return video_list, duration, audio_list, subs_list

video_list, duration, audio_list, subs_list = parse_mpd(mpd_url)

print(YELLOW)
for video in video_list:
    video_bandwidth = video['Bandwidth']
    video_height = int(video['Height'])
    video_width = int(video['Width'])
    video_codec = video['Codec']
    video_framerate = video['FrameRate']
    video_size_gb = (duration * float(video_bandwidth) * 0.125) / (1024 ** 3)

    print('VIDEO - Bitrate: {} kbps | Codec: {} | Size: {:.2f} GiB | Resolution: {}x{} | FPS: {:.3f} | DRM: True'.format(
        convert_size(int(video_bandwidth)),
        video_codec,
        video_size_gb,
        video_width,
        video_height,
        float(video_framerate)
    ))

print()

if audio_list != []:
    for audio in audio_list:
        lang_id = audio['ID'].split("/")

        if "audio" in lang_id:
            audio_language = lang_id[1]
        else:
            audio_language = 'und'

        print('AUDIO - Bitrate: {} | Codec: {} | Size: {} | Channels: {} | Language: {}'.format(
            convert_size(int(audio['Bandwidth'])),
            audio['Codec'],
            get_size(duration * float(audio['Bandwidth']) * 0.125),
            audio['Channels'],
            audio_language
            ))
    print()

if subs_list != []:
    for subtitle in subs_list:
        print('SUBTITLE - ID: {} | Language: {} | Format: {}'.format(
             subtitle['ID'], subtitle['Language'], subtitle['Format']))
    print()
print(RESET)