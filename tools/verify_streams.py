#!/usr/bin/env python3
"""
Verify streams return 200 AND have real video content
Uses only standard libraries
"""
import urllib.request
import json
import subprocess
import tempfile

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (SMART-TV) AppleWebKit/537.36',
}

def check_http_200(url: str) -> tuple[bool, int]:
    """Check if URL returns 200"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return (resp.status == 200, resp.status)
    except Exception as e:
        return (False, 0)

def check_video_content(url: str) -> tuple[bool, str]:
    """Check if stream has real video content using ffmpeg"""
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', url,
            '-t', '3',
            '-vf', 'fps=1,scale=160:90',
            '-f', 'mjpeg',
            '-'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=20
        )
        
        if result.returncode != 0:
            return False, f"ffmpeg error: {result.returncode}"
        
        if len(result.stdout) < 1000:
            return False, "no frames captured"
        
        return True, f"got {len(result.stdout)} bytes"
    
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except FileNotFoundError:
        return False, "ffmpeg not found"
    except Exception as e:
        return False, str(e)

def verify_stream(url: str, channel_name: str = '', category: str = '') -> dict:
    """Full verification of a stream"""
    result = {
        'url': url,
        'channel': channel_name,
        'category': category,
        'http_200': False,
        'http_status': 0,
        'has_video': False,
        'video_detail': '',
        'working': False
    }
    
    print(f"  Checking HTTP: {url[:60]}...")
    http_ok, status = check_http_200(url)
    result['http_200'] = http_ok
    result['http_status'] = status
    
    if not http_ok:
        print(f"  -> HTTP {status} - NO VIDEO CHECK")
        return result
    
    print(f"  HTTP 200 OK, checking video content...")
    has_video, detail = check_video_content(url)
    result['has_video'] = has_video
    result['video_detail'] = detail
    result['working'] = http_ok and has_video
    
    print(f"  -> VIDEO: {detail}")
    
    return result

def main():
    channels_file = '/data/data/com.termux/files/home/MoJiTo/premium_working.json'
    print(f"Loading: {channels_file}")
    
    with open(channels_file, 'r') as f:
        data = json.load(f)
    
    print(f"Channels to verify: {len(data['channels'])}")
    
    all_results = []
    working = []
    failed = []
    
    for ch in data['channels']:
        url = ch['url']
        name = ch['name']
        category = ch.get('category', '')
        
        print(f"\n[{name}] Primary: {url}")
        result = verify_stream(url, name, category)
        all_results.append(result)
        
        if result['working']:
            working.append(result)
        else:
            failed.append(result)
        
        for fb_url in ch.get('fallbacks', []):
            print(f"  [Fallback] {fb_url}")
            fb_result = verify_stream(fb_url, name, category)
            all_results.append(fb_result)
            
            if fb_result['working'] and not result['working']:
                working.append(fb_result)
            else:
                failed.append(fb_result)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Working (200 + video): {len(working)}")
    print(f"  Failed: {len(failed)}")
    
    output = {
        'working_count': len(working),
        'working': working,
        'failed_count': len(failed),
        'failed': failed,
    }
    
    output_file = '/data/data/com.termux/files/home/MoJiTo/verified_streams.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSaved to: {output_file}")
    
    print(f"\nWORKING CHANNELS ({len(working)}):")
    for w in working:
        print(f"  - {w['channel']} ({w['category']}): {w['url']}")

if __name__ == '__main__':
    main()