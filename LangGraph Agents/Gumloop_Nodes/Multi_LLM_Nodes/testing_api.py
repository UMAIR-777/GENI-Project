import os
import time
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def upload_to_gemini(path, mime_type=None):
  """Uploads the given file to Gemini.

  See https://ai.google.dev/gemini-api/docs/prompting_with_media
  """
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  return file

def wait_for_files_active(files):
  """Waits for the given files to be active.

  Some files uploaded to the Gemini API need to be processed before they can be
  used as prompt inputs. The status can be seen by querying the file's "state"
  field.

  This implementation uses a simple blocking polling loop. Production code
  should probably employ a more sophisticated approach.
  """
  print("Waiting for file processing...")
  for name in (file.name for file in files):
    file = genai.get_file(name)
    while file.state.name == "PROCESSING":
      print(".", end="", flush=True)
      time.sleep(10)
      file = genai.get_file(name)
    if file.state.name != "ACTIVE":
      raise Exception(f"File {file.name} failed to process")
  print("...all files ready")
  print()

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-pro",
  generation_config=generation_config,
)

# TODO Make these files available on the local file system
# You may need to update the file paths
files = [
  upload_to_gemini("Sherlock Jr. (1924) - 10 Min Clip", mime_type="video/mp4"),
]

# Some files have a processing delay. Wait for them to be ready.
wait_for_files_active(files)

chat_session = model.start_chat(
  history=[
    {
      "role": "user",
      "parts": [
        files[0],
      ],
    },
    {
      "role": "user",
      "parts": [
        "descripe what is happening in the video\n",
      ],
    },
    {
      "role": "model",
      "parts": [
        "Here’s a description of the events in the video:\n\nBuster Keaton, a projectionist, has aspirations of becoming a detective, so he reads a book of detective tips, and then shadows a man from a neighboring house. He follows the man through the streets, crosses the road, and then follows him past the railroad tracks. Buster follows the man into a station baggage room and then onto the platform where he climbs on top of a moving train. He climbs up a water tower, loses his grip and falls into a trough filled with water. He returns to the cinema where he works and puts the projector on autopilot while he falls asleep. He dreams he is a great detective called Sherlock Jr. and is hired to find stolen pearls. He examines several scenes within the dream, some taken from the film he is projecting, including a desert, a cliff edge, and a lion’s den. He recognizes the man from earlier in his dream, where he is now a rich man, and is able to track down the thief. ",
      ],
    },
  ]
)

response = chat_session.send_message("INSERT_INPUT_HERE")

print(response.text)