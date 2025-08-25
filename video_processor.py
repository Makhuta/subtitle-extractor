import os
import logging
import ffmpeg
from typing import List, Dict, Optional
import subprocess
import json

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Handles video file processing and subtitle extraction using FFmpeg"""
    
    def __init__(self):
        self.ffmpeg_path = 'ffmpeg'
        self.ffprobe_path = 'ffprobe'
    
    def get_subtitle_tracks(self, video_path: str) -> List[Dict]:
        """
        Extract information about subtitle tracks in a video file
        
        Args:
            video_path: Path to the video file
            
        Returns:
            List of subtitle track information dictionaries
        """
        try:
            # Use ffprobe to get subtitle stream information
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-select_streams', 's',  # Select only subtitle streams
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"ffprobe failed: {result.stderr}")
                return []
            
            data = json.loads(result.stdout)
            subtitle_tracks = []
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'subtitle':
                    track_info = {
                        'index': stream.get('index'),
                        'codec_name': stream.get('codec_name', 'unknown'),
                        'language': stream.get('tags', {}).get('language', 'unknown'),
                        'title': stream.get('tags', {}).get('title', ''),
                        'forced': stream.get('disposition', {}).get('forced', 0) == 1,
                        'default': stream.get('disposition', {}).get('default', 0) == 1
                    }
                    subtitle_tracks.append(track_info)
            
            logger.info(f"Found {len(subtitle_tracks)} subtitle tracks in {video_path}")
            return subtitle_tracks
            
        except Exception as e:
            logger.error(f"Error getting subtitle tracks: {str(e)}")
            return []
    
    def extract_subtitle(self, video_path: str, track_index: int) -> Optional[str]:
        """
        Extract subtitle content from a specific track
        
        Args:
            video_path: Path to the video file
            track_index: Index of the subtitle track to extract
            
        Returns:
            Subtitle content as string, or None if extraction failed
        """
        try:
            # Use ffmpeg to extract subtitle to stdout
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-map', f'0:{track_index}',  # Map specific subtitle stream
                '-c:s', 'copy',  # Copy subtitle codec
                '-f', 'ass',  # Force ASS format output
                '-'  # Output to stdout
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"ffmpeg extraction failed: {result.stderr}")
                
                # Try alternative method - extract as SRT first then convert
                return self._extract_as_srt_then_convert(video_path, track_index)
            
            content = result.stdout
            
            if not content or len(content.strip()) == 0:
                logger.warning("Extracted subtitle content is empty")
                return None
            
            logger.info(f"Successfully extracted subtitle from track {track_index}")
            return content
            
        except Exception as e:
            logger.error(f"Error extracting subtitle: {str(e)}")
            return None
    
    def _extract_as_srt_then_convert(self, video_path: str, track_index: int) -> Optional[str]:
        """
        Fallback method: extract as SRT then convert to ASS format
        
        Args:
            video_path: Path to the video file
            track_index: Index of the subtitle track to extract
            
        Returns:
            Subtitle content in ASS format, or None if extraction failed
        """
        try:
            # Extract as SRT first
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-map', f'0:{track_index}',
                '-c:s', 'srt',
                '-f', 'srt',
                '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"SRT extraction also failed: {result.stderr}")
                return None
            
            srt_content = result.stdout
            
            if not srt_content or len(srt_content.strip()) == 0:
                return None
            
            # Convert SRT to basic ASS format
            ass_content = self._convert_srt_to_ass(srt_content)
            
            logger.info(f"Successfully extracted and converted subtitle from track {track_index}")
            return ass_content
            
        except Exception as e:
            logger.error(f"Error in fallback extraction: {str(e)}")
            return None
    
    def _convert_srt_to_ass(self, srt_content: str) -> str:
        """
        Convert SRT content to basic ASS format
        
        Args:
            srt_content: SRT subtitle content
            
        Returns:
            ASS formatted subtitle content
        """
        try:
            # Basic ASS header
            ass_header = """[Script Info]
Title: Extracted Subtitle
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,16,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            
            # Parse SRT and convert to ASS events
            events = []
            srt_blocks = srt_content.strip().split('\n\n')
            
            for block in srt_blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    # Parse timing line (line 1, 0-indexed)
                    timing_line = lines[1]
                    if ' --> ' in timing_line:
                        start_time, end_time = timing_line.split(' --> ')
                        
                        # Convert SRT time format to ASS time format
                        start_ass = self._srt_time_to_ass(start_time.strip())
                        end_ass = self._srt_time_to_ass(end_time.strip())
                        
                        # Combine text lines (skip index and timing)
                        text = '\\N'.join(lines[2:])
                        
                        # Create ASS dialogue line
                        event = f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text}"
                        events.append(event)
            
            return ass_header + '\n'.join(events)
            
        except Exception as e:
            logger.error(f"Error converting SRT to ASS: {str(e)}")
            return srt_content  # Return original if conversion fails
    
    def _srt_time_to_ass(self, srt_time: str) -> str:
        """
        Convert SRT time format to ASS time format
        
        Args:
            srt_time: Time in SRT format (HH:MM:SS,mmm)
            
        Returns:
            Time in ASS format (H:MM:SS.mm)
        """
        try:
            # SRT format: HH:MM:SS,mmm
            # ASS format: H:MM:SS.mm
            
            time_part, ms_part = srt_time.split(',')
            hours, minutes, seconds = time_part.split(':')
            
            # Convert milliseconds to centiseconds (ASS uses centiseconds)
            centiseconds = str(int(ms_part) // 10).zfill(2)
            
            # Remove leading zero from hours if present
            hours = str(int(hours))
            
            return f"{hours}:{minutes}:{seconds}.{centiseconds}"
            
        except Exception as e:
            logger.error(f"Error converting time format: {str(e)}")
            return srt_time
