from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import re

def fetch_transcript(youtube_url):
    '''
    Description:
    This function takes in a youtube video URL and does the following:
    -> Extracts the video ID from the URL
    -> Uses the video ID and gets the video transcript 
    -> Returns the transcript.

    Args: youtube_url (https://www.youtube.com/VIDEO_ID)

    '''
    match = re.search(r'(?:v=|youtu\.be/|embed/|watch\?v=)([^&\n?#]+)', youtube_url)
    video_id =  match.group(1) if match else None
    if not video_id:
        return "Invalid YouTube URL"
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en-US'])
        formatter = TextFormatter()
        formatted_transcript = formatter.format_transcript(transcript)
        return formatted_transcript
    except Exception as e:
        return f"Error: {e}"


#JSON:

# {'id': 'Get_Youtube_Transcript',
#             'type': 'runnable',
#             'data': {'id': ['langgraph',
#                             'utils',
#                             'runnable',
#                             'RunnableCallable'],
#                      'name': 'create_plan',
#                      },
#             'inputs': {
#                 'youtube_url': ''
#             },
# 'output': {
# 	'transcript': ''
# }
# }