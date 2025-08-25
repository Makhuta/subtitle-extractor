import re
import logging
from typing import List, Dict, Optional, Tuple
import pysubs2
from io import StringIO

logger = logging.getLogger(__name__)

class SubtitleProcessor:
    """Handles subtitle parsing, matching, and generation"""
    
    def __init__(self):
        pass
    
    def parse_ass_content(self, content: str) -> List[Dict]:
        """
        Parse ASS subtitle content into structured data
        
        Args:
            content: ASS subtitle content as string
            
        Returns:
            List of subtitle line dictionaries
        """
        try:
            # Use pysubs2 to parse ASS content
            subs = pysubs2.SSAFile.from_string(content)
            
            lines = []
            for i, line in enumerate(subs):
                line_data = {
                    'index': i,
                    'start': line.start,  # in milliseconds
                    'end': line.end,      # in milliseconds
                    'character': line.name or '',
                    'text': line.plaintext,
                    'style': line.style,
                    'original_text': line.text,  # Keep original with formatting
                    'layer': getattr(line, 'layer', 0),
                    'margin_l': getattr(line, 'margin_l', 0),
                    'margin_r': getattr(line, 'margin_r', 0),
                    'margin_v': getattr(line, 'margin_v', 0),
                    'effect': getattr(line, 'effect', ''),
                    'translation': ''  # Will be filled during matching
                }
                lines.append(line_data)
            
            logger.info(f"Parsed {len(lines)} lines from ASS content")
            return lines
            
        except Exception as e:
            logger.error(f"Error parsing ASS content: {str(e)}")
            # Fallback to manual parsing if pysubs2 fails
            return self._manual_parse_ass(content)
    
    def _manual_parse_ass(self, content: str) -> List[Dict]:
        """
        Manual parsing of ASS content as fallback
        
        Args:
            content: ASS subtitle content
            
        Returns:
            List of subtitle line dictionaries
        """
        try:
            lines = []
            dialogue_lines = []
            
            # Find dialogue lines
            for line in content.split('\n'):
                if line.strip().startswith('Dialogue:'):
                    dialogue_lines.append(line.strip())
            
            for i, line in enumerate(dialogue_lines):
                try:
                    # Parse dialogue line format:
                    # Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
                    parts = line.split(',', 9)  # Split on first 9 commas
                    
                    if len(parts) >= 10:
                        start_time = self._ass_time_to_ms(parts[1])
                        end_time = self._ass_time_to_ms(parts[2])
                        style = parts[3]
                        character = parts[4]
                        text = parts[9]
                        
                        line_data = {
                            'index': i,
                            'start': start_time,
                            'end': end_time,
                            'character': character,
                            'text': self._strip_ass_formatting(text),
                            'style': style,
                            'original_text': text,
                            'layer': int(parts[0].split(':')[1]) if ':' in parts[0] else 0,
                            'margin_l': int(parts[5]) if parts[5].isdigit() else 0,
                            'margin_r': int(parts[6]) if parts[6].isdigit() else 0,
                            'margin_v': int(parts[7]) if parts[7].isdigit() else 0,
                            'effect': parts[8],
                            'translation': ''
                        }
                        lines.append(line_data)
                except Exception as e:
                    logger.warning(f"Error parsing dialogue line {i}: {str(e)}")
                    continue
            
            logger.info(f"Manually parsed {len(lines)} lines from ASS content")
            return lines
            
        except Exception as e:
            logger.error(f"Error in manual ASS parsing: {str(e)}")
            return []
    
    def parse_subtitle_content(self, content: str, file_extension: str) -> List[Dict]:
        """
        Parse subtitle content from various formats
        
        Args:
            content: Subtitle file content
            file_extension: File extension (.srt, .vtt, .ass, etc.)
            
        Returns:
            List of subtitle line dictionaries
        """
        try:
            if file_extension.lower() == '.ass':
                return self.parse_ass_content(content)
            
            # Use pysubs2 for other formats
            subs = pysubs2.SSAFile.from_string(content)
            
            lines = []
            for i, line in enumerate(subs):
                line_data = {
                    'index': i,
                    'start': line.start,
                    'end': line.end,
                    'character': '',
                    'text': line.plaintext,
                    'original_text': line.text
                }
                lines.append(line_data)
            
            logger.info(f"Parsed {len(lines)} lines from {file_extension} content")
            return lines
            
        except Exception as e:
            logger.error(f"Error parsing subtitle content: {str(e)}")
            return []
    
    def match_subtitles(self, original_lines: List[Dict], translation_lines: List[Dict], tolerance: int = 1000) -> List[Dict]:
        """
        Match original and translation subtitle lines based on timing
        
        Args:
            original_lines: List of original subtitle lines
            translation_lines: List of translation subtitle lines
            tolerance: Time tolerance in milliseconds for matching
            
        Returns:
            List of matched subtitle lines with translations
        """
        try:
            matched_lines = []
            
            for orig_line in original_lines:
                best_match = None
                best_score = float('inf')
                
                orig_start = orig_line['start']
                orig_end = orig_line['end']
                orig_mid = (orig_start + orig_end) / 2
                
                # Find best matching translation line
                for trans_line in translation_lines:
                    trans_start = trans_line['start']
                    trans_end = trans_line['end']
                    trans_mid = (trans_start + trans_end) / 2
                    
                    # Calculate time difference
                    time_diff = abs(orig_mid - trans_mid)
                    
                    if time_diff <= tolerance and time_diff < best_score:
                        best_score = time_diff
                        best_match = trans_line
                
                # Create matched line
                matched_line = orig_line.copy()
                if best_match:
                    matched_line['translation'] = best_match['text']
                    matched_line['translation_start'] = best_match['start']
                    matched_line['translation_end'] = best_match['end']
                    matched_line['time_diff'] = best_score
                else:
                    matched_line['translation'] = ''
                
                matched_lines.append(matched_line)
            
            matched_count = len([line for line in matched_lines if line['translation']])
            logger.info(f"Matched {matched_count}/{len(original_lines)} lines with tolerance {tolerance}ms")
            
            return matched_lines
            
        except Exception as e:
            logger.error(f"Error matching subtitles: {str(e)}")
            return original_lines
    
    def generate_final_ass(self, original_content: str, matched_lines: List[Dict]) -> str:
        """
        Generate final ASS subtitle file with modifications
        
        Args:
            original_content: Original ASS content
            matched_lines: List of matched and edited subtitle lines
            
        Returns:
            Final ASS content as string
        """
        try:
            # Parse original content to get header and styles
            lines = original_content.split('\n')
            header_lines = []
            events_started = False
            
            # Extract header and styles (everything before [Events])
            for line in lines:
                if line.strip().startswith('[Events]'):
                    events_started = True
                    header_lines.append(line)
                    # Find and add format line
                    continue
                elif events_started and line.strip().startswith('Format:'):
                    header_lines.append(line)
                    break
                elif not events_started:
                    header_lines.append(line)
            
            # Build new dialogue lines
            dialogue_lines = []
            for line_data in matched_lines:
                # Use translation if available, otherwise use original text
                final_text = line_data.get('translation', '').strip()
                if not final_text:
                    final_text = line_data.get('original_text', line_data.get('text', ''))
                
                # Format time
                start_time = self._ms_to_ass_time(line_data['start'])
                end_time = self._ms_to_ass_time(line_data['end'])
                
                # Build dialogue line
                dialogue = (
                    f"Dialogue: {line_data.get('layer', 0)},"
                    f"{start_time},{end_time},"
                    f"{line_data.get('style', 'Default')},"
                    f"{line_data.get('character', '')},"
                    f"{line_data.get('margin_l', 0)},"
                    f"{line_data.get('margin_r', 0)},"
                    f"{line_data.get('margin_v', 0)},"
                    f"{line_data.get('effect', '')},"
                    f"{final_text}"
                )
                dialogue_lines.append(dialogue)
            
            # Combine header and new dialogue lines
            final_content = '\n'.join(header_lines + dialogue_lines)
            
            logger.info(f"Generated final ASS content with {len(dialogue_lines)} lines")
            return final_content
            
        except Exception as e:
            logger.error(f"Error generating final ASS: {str(e)}")
            # Return original content as fallback
            return original_content
    
    def _ass_time_to_ms(self, time_str: str) -> int:
        """Convert ASS time format to milliseconds"""
        try:
            # ASS format: H:MM:SS.mm
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            centiseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
            
            total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + centiseconds * 10
            return total_ms
        except Exception as e:
            logger.error(f"Error converting ASS time to ms: {str(e)}")
            return 0
    
    def _ms_to_ass_time(self, ms: int) -> str:
        """Convert milliseconds to ASS time format"""
        try:
            total_seconds = ms // 1000
            centiseconds = (ms % 1000) // 10
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
        except Exception as e:
            logger.error(f"Error converting ms to ASS time: {str(e)}")
            return "0:00:00.00"
    
    def _strip_ass_formatting(self, text: str) -> str:
        """Remove ASS formatting tags from text"""
        try:
            # Remove ASS override tags like {\b1}, {\i1}, {\c&H...}, etc.
            clean_text = re.sub(r'\{[^}]*\}', '', text)
            # Replace \N with space for plain text
            clean_text = clean_text.replace('\\N', ' ')
            return clean_text.strip()
        except Exception as e:
            logger.error(f"Error stripping ASS formatting: {str(e)}")
            return text
