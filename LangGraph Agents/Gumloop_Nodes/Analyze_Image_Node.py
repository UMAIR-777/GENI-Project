import google.generativeai as genai
import time
#Inputs:

# Image File: Upload image (JPG, PNG, GIF, or WEBP)
# Prompt: Question or instruction for analysis. Be detailed here for accurate output

# NOTE: 
# API KEYS ARE ONLY EXPOSED FOR DEV PURPOSES THEY WILL BE REMOVED LATER!

GOOGLE_API_KEY='AIzaSyAQCGArejXmGGKaDO_OR9hq_XasPqLiemg'
genai.configure(api_key=GOOGLE_API_KEY)

def analyze_image(image_file, prompt):

    image_file = image_file
    prompt = prompt

    # Set up the model:
    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

    image_content = genai.upload_file(path=image_file,display_name="User Image")

    print(f"Uploaded file '{image_content.display_name}' as: {image_content.uri}")

    file = genai.get_file(name=image_content.name)

    response = model.generate_content([prompt, image_content])
    
    return response.text


# prompt = "Identify the scenes in the image and provide a detailed description"
# image_file_path = r'C:\Users\User\Desktop\LangGraph_Codet\ai-workflow-research-py\LangGraph Agents\Gumloop_Nodes\Multi_LLM_Nodes\img.jpg'

# response_text = analyze_image(image_file_path,prompt)
# print(response_text)