import google.generativeai as genai
import time
#Inputs:

# Video File: Upload video (FLV, QuickTime, MPEG, MPEGPS, MPG, MP4, WEBM, WMV, or 3GPP)
# Prompt: Question or instruction for analysis. Be specific for best results
# Video Model: Choose AI model for analysis (Gemini 1.5 Flash/Pro)

# NOTE: 
# API KEYS ARE ONLY EXPOSED FOR DEV PURPOSES THEY WILL BE REMOVED LATER!

GOOGLE_API_KEY='AIzaSyAQCGArejXmGGKaDO_OR9hq_XasPqLiemg'
genai.configure(api_key=GOOGLE_API_KEY)

def analyze_video(video_file, prompt,video_model='gemini'):

    video_file = video_file
    prompt = prompt
    video_model = video_model

    if video_model != 'gemini':
        # Logic for other model connection
        pass
    else:
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
        video_file_name = video_file
        print(f"Uploading file to Analyze...")
        video_file = genai.upload_file(path=video_file_name)
        print(f"Completed upload!: {video_file.uri}")

        while video_file.state.name == "PROCESSING":
            print('.', end='')
            time.sleep(10)
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            raise ValueError(video_file.state.name)

        print("Analyzing The Request...")
        response = model.generate_content([prompt, video_file],
                                        request_options={"timeout": 600})
        
        #Delete the video file after processing:
        genai.delete_file(video_file.name)
        
        return response.text


# prompt = "Analyze the video and provide a detailed report."
# video_file_path = r"855633-hd_1920_1080_25fps.mp4"

# response_text = analyze_video(video_file_path,prompt)
# print(response_text)