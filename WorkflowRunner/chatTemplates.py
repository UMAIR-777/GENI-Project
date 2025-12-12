# File Name: chat_templates.py
# Purpose: Store predefined chat templates or prompts for functions like Ask_AI, summarize, etc.
# _________________________________________________________________________________________________
# template file
from langchain_core.prompts import ChatPromptTemplate

def write_post_template(post_system_prompt,postTopic, targetAudience):
  prompt_template = ChatPromptTemplate([
    ("system", post_system_prompt),
    ("human", "Write a highly engaging and SEO-friendly post on the topic: '{postTopic}' for the target audience: '{targetAudience}'. The post should include a captivating introduction that speaks directly to the audience's needs or interests, well-structured content with subheadings or bullet points where applicable, and a strong conclusion with a call to action. Use language, tone, and examples that are relatable for the audience, naturally incorporate relevant keywords, and ensure readability through concise paragraphs and clear transitions.")])

  return prompt_template.invoke({"postTopic" : postTopic, "targetAudience" : targetAudience})

def summarize_template(summarize_system_prompt,input_summary_text):
  prompt_template = ChatPromptTemplate([
    ("system", summarize_system_prompt),
    ("human", '{input_summary_text}')])

  return prompt_template.invoke({"input_summary_text" : input_summary_text})




