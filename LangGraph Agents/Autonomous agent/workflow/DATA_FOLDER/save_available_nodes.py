import json
import os

AVAILABLE_NODES = [
    {
        "id": "analyze_image",
        "input": ["image_file", "prompt"],
        "output": ["image_analysis"],
        "tags": ["Image Analysis", "AI", "Computer Vision"],
        "description": [
            "Analyzes an image using advanced AI models.",
            "Provides detailed insights including object detection and scene interpretation.",
            "Ideal for automated image classification and visual content assessment."
        ],
        "spo": {
            "subject": "Automated image analysis tool",
            "predicate": "analyzes images using AI models",
            "object": "for object detection, scene interpretation, and visual content assessment"
        }
    },
    {
        "id": "website_scraper",
        "input": ["website_url"],
        "output": ["website_scraped_content"],
        "tags": ["Web Scraping", "Data Extraction", "Scraping"],
        "description": [
            "Scrapes content from websites by retrieving and parsing webpage data.",
            "Extracts structured information for further analysis and research.",
            "Suitable for data mining and competitive intelligence tasks."
        ],
        "spo": {
            "subject": "Automated web scraper",
            "predicate": "extracts and structures online content",
            "object": "for research, data mining, and competitive intelligence"
        }
    },
    {
        "id": "analyze_video",
        "input": ["video_file_url", "prompt", "video_model"],
        "output": ["video_analysis"],
        "tags": ["Video Analysis", "AI", "Multimedia"],
        "description": [
            "Analyzes video content using specialized AI models.",
            "Extracts insights and generates detailed analytical results.",
            "Optimized for multimedia content analysis and video summarization."
        ],
        "spo": {
            "subject": "Automated video analysis tool",
            "predicate": "analyzes video content using specialized AI models",
            "object": "for video summarization and multimedia content analysis"
        }
    },
    {
        "id": "Ask_AI",
        "input": ["prompt", "context"],
        "output": ["ai_response", "generated_text", "AI"],
        "tags": ["Chatbot", "AI Interaction", "Conversational AI"],
        "description": [
            "Interacts with a language model to generate answers or creative text.",
            "Facilitates dynamic dialogue and contextual summarization.",
            "Enhances user engagement with context-aware responses."
        ],
        "spo": {
            "subject": "AI-powered chatbot",
            "predicate": "generates answers and creative text",
            "object": "for dynamic dialogue and context-aware responses"
        }
    },
    {
        "id": "Blog_Writer",
        "input": ["Content", "Target_Audience", "Tone", "Content_Length"],
        "output": ["blog", "blog_content", "blog_post"],
        "tags": ["Content Creation", "AI Writing", "Blog Writing"],
        "description": [
            "Generates comprehensive blog posts based on provided parameters.",
            "Creates engaging and targeted content for marketing and communication.",
            "Automates the writing process for consistent and creative outputs."
        ],
        "spo": {
            "subject": "AI blog writer",
            "predicate": "generates comprehensive blog posts",
            "object": "for marketing, communication, and consistent content creation"
        }
    },
    {
        "id": "Get_Youtube_Transcript",
        "input": ["youtube_url", "video_url"],
        "output": ["transcript"],
        "tags": ["YouTube", "Transcription", "Video Transcript"],
        "description": [
            "Retrieves the transcript from a YouTube video URL.",
            "Efficiently extracts textual content for downstream analysis.",
            "Facilitates accurate video content processing and transcription tasks."
        ],
        "spo": {
            "subject": "Automated YouTube transcript retriever",
            "predicate": "extracts transcripts from YouTube videos",
            "object": "for video content processing and transcription tasks"
        }
    },
    {
        "id": "summarize",
        "input": ["transcript", "content", "inputText"],
        "output": ["summary"],
        "tags": ["Text Summarization", "AI", "Summarization"],
        "description": [
            "Summarizes lengthy text, transcripts, or content using AI.",
            "Condenses information while retaining key points and context.",
            "Effective for producing concise summaries from extensive data."
        ],
        "spo": {
            "subject": "AI summarization tool",
            "predicate": "summarizes text and transcripts",
            "object": "for condensing information while retaining key points"
        }
    },
    {
        "id": "generate_keywords",
        "input": ["text", "content"],
        "output": ["keywords"],
        "tags": ["Keyword Generation", "AI", "Keyword Extraction"],
        "description": [
            "Generates relevant keywords from a given text.",
            "Optimizes and enhances content tagging for improved retrieval.",
            "Supports targeted marketing and efficient data indexing."
        ],
        "spo": {
            "subject": "AI keyword generator",
            "predicate": "generates relevant keywords from text",
            "object": "for content optimization and efficient content tagging"
        }
    }
]

data_folder = "Data_Folder"
os.makedirs(data_folder, exist_ok=True)
file_path = os.path.join(data_folder, "available_nodes.json")

with open(file_path, 'w') as f:
    json.dump(AVAILABLE_NODES, f, indent=4)

print(f"AVAILABLE_NODES have been saved to: {file_path}")