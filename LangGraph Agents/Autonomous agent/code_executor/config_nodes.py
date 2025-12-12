
# Update with all Node JSON:
AVAILABLE_NODES = [
    # Data Retrieval Nodes
    {
        "id": "Get_Youtube_Transcript",
        "inputs": {"youtube_url": ""},
        "output": {"transcript": ""}
    },
    {
        "id": "Website_Scraper",
        "inputs": {"website_url": "", "selector": ""},
        "output": {"scraped_content": ""}
    },
    {
        "id": "Fetch_API",
        "inputs": {"api_url": "", "method": "", "headers": "", "body": ""},
        "output": {"api_response": ""}
    },
    {
        "id": "Read_RSS_Feed",
        "inputs": {"feed_url": ""},
        "output": {"feed_items": ""}
    },
    {
        "id": "Get_Twitter_Posts",
        "inputs": {"username": "", "count": ""},
        "output": {"tweets": ""}
    },

    # Text Processing Nodes
    {
        "id": "Summarize_Text",
        "inputs": {"input_text": ""},
        "output": {"summary": ""}
    },
    {
        "id": "Extract_Keywords",
        "inputs": {"text": ""},
        "output": {"keywords": ""}
    },
    {
        "id": "Text_Formatter",
        "inputs": {"text": "", "format_type": ""},
        "output": {"formatted_text": ""}
    },
    {
        "id": "Translate_Text",
        "inputs": {"text": "", "target_language": ""},
        "output": {"translated_text": ""}
    },
    {
        "id": "Sentiment_Analysis",
        "inputs": {"text": ""},
        "output": {"sentiment_score": ""}
    },

    # AI Interaction Nodes
    {
        "id": "Ask_AI",
        "inputs": {"prompt": "", "context": ""},
        "output": {"ai_response": ""}
    },
    {
        "id": "Generate_Text",
        "inputs": {"prompt": "", "length": "", "tone": ""},
        "output": {"generated_text": ""}
    },
    {
        "id": "Classify_Text",
        "inputs": {"text": "", "model": ""},
        "output": {"classification": ""}
    },
    {
        "id": "Generate_Image",
        "inputs": {"prompt": "", "style": ""},
        "output": {"image_url": ""}
    },
    {
        "id": "Analyze_Image",
        "inputs": {"image_file": "", "prompt": ""},
        "output": {"image_analysis": ""}
    },

    # Content Creation Nodes
    {
        "id": "Blog_Writer",
        "inputs": {"content": "", "target_audience": "", "tone": "", "length": ""},
        "output": {"blog_post": ""}
    },
    {
        "id": "Email_Writer",
        "inputs": {"subject": "", "body": "", "tone": ""},
        "output": {"email_content": ""}
    },
    {
        "id": "Social_Media_Post",
        "inputs": {"content": "", "platform": "", "tone": ""},
        "output": {"post_text": ""}
    },
    {
        "id": "SEO_Optimizer",
        "inputs": {"content": "", "keywords": ""},
        "output": {"optimized_content": ""}
    },
    {
        "id": "Generate_Title",
        "inputs": {"content": "", "style": ""},
        "output": {"title": ""}
    },

    # File Handling Nodes
    {
        "id": "Read_File",
        "inputs": {"file_path": ""},
        "output": {"file_content": ""}
    },
    {
        "id": "Write_File",
        "inputs": {"content": "", "file_path": ""},
        "output": {"status": ""}
    },
    {
        "id": "Convert_File",
        "inputs": {"file_path": "", "format": ""},
        "output": {"converted_file": ""}
    },
    {
        "id": "Upload_File",
        "inputs": {"file_path": "", "destination": ""},
        "output": {"upload_status": ""}
    },
    {
        "id": "Download_File",
        "inputs": {"url": "", "save_path": ""},
        "output": {"file_path": ""}
    },

    # Data Manipulation Nodes
    {
        "id": "Filter_Data",
        "inputs": {"data": "", "condition": ""},
        "output": {"filtered_data": ""}
    },
    {
        "id": "Sort_Data",
        "inputs": {"data": "", "key": "", "order": ""},
        "output": {"sorted_data": ""}
    },
    {
        "id": "Merge_Data",
        "inputs": {"data1": "", "data2": "", "merge_key": ""},
        "output": {"merged_data": ""}
    },
    {
        "id": "Split_Text",
        "inputs": {"text": "", "delimiter": ""},
        "output": {"text_list": ""}
    },
    {
        "id": "JSON_Parser",
        "inputs": {"json_string": ""},
        "output": {"parsed_data": ""}
    },

    # Integration Nodes
    {
        "id": "Send_Email",
        "inputs": {"to": "", "subject": "", "body": ""},
        "output": {"send_status": ""}
    },
    {
        "id": "Post_Slack",
        "inputs": {"channel": "", "message": ""},
        "output": {"post_status": ""}
    },
    {
        "id": "Create_Google_Doc",
        "inputs": {"title": "", "content": ""},
        "output": {"doc_url": ""}
    },
    {
        "id": "Update_Spreadsheet",
        "inputs": {"sheet_id": "", "data": ""},
        "output": {"update_status": ""}
    },
    {
        "id": "Webhook_Trigger",
        "inputs": {"url": "", "payload": ""},
        "output": {"response": ""}
    },

    # Conditional & Logic Nodes
    {
        "id": "If_Condition",
        "inputs": {"value": "", "condition": "", "threshold": ""},
        "output": {"result": ""}
    },
    {
        "id": "Switch_Case",
        "inputs": {"value": "", "cases": ""},
        "output": {"selected_output": ""}
    },
    {
        "id": "Loop",
        "inputs": {"items": "", "action": ""},
        "output": {"loop_results": ""}
    },
    {
        "id": "Delay",
        "inputs": {"duration": ""},
        "output": {"status": ""}
    },
    {
        "id": "Error_Handler",
        "inputs": {"input": ""},
        "output": {"handled_output": ""}
    },

    # Advanced Analysis Nodes
    {
        "id": "Analyze_Video",
        "inputs": {"video_file": "", "prompt": "", "model": ""},
        "output": {"video_analysis": ""}
    },
    {
        "id": "Extract_Audio",
        "inputs": {"video_file": ""},
        "output": {"audio_file": ""}
    },
    {
        "id": "Speech_to_Text",
        "inputs": {"audio_file": ""},
        "output": {"transcript": ""}
    },
    {
        "id": "Data_Visualization",
        "inputs": {"data": "", "chart_type": ""},
        "output": {"chart_url": ""}
    },
    {
        "id": "Trend_Analysis",
        "inputs": {"data": "", "time_period": ""},
        "output": {"trend_report": ""}
    },

    # Miscellaneous Nodes
    {
        "id": "Random_Generator",
        "inputs": {"type": "", "range": ""},
        "output": {"random_value": ""}
    },
    {
        "id": "Date_Time",
        "inputs": {"format": ""},
        "output": {"datetime": ""}
    },
    {
        "id": "Counter",
        "inputs": {"start": "", "increment": ""},
        "output": {"count": ""}
    },
    {
        "id": "Logger",
        "inputs": {"message": ""},
        "output": {"log_status": ""}
    },
    {
        "id": "Notify",
        "inputs": {"message": "", "method": ""},
        "output": {"notify_status": ""}
    }
]