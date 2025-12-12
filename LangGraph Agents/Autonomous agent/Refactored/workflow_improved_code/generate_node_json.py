import os
import json
from pathlib import Path
from src.template_renderer import TemplateRenderer
from src.ai_service import AIService

def main():
    # Initialize TemplateRenderer with prompts directory
    prompts_dir = Path(__file__).parent / "src" / "prompts"
    renderer = TemplateRenderer(prompts_dir=str(prompts_dir))

    # Initialize AIService (model from environment variable MODEL_USED)
    ai_service = AIService()

    # Directory containing node code files
    nodes_dir = Path(__file__).parent / "src" / "sample_nodes_dir"

    # Load the prompt template name
    prompt_template = "subtask/create_JSON_from_node.jinja2"

    node_jsons = []

    # Iterate over each Python file in nodes_dir
    for node_file in nodes_dir.glob("*.py"):
        with open(node_file, "r", encoding="utf-8") as f:
            code_content = f.read()

        # Render the prompt with the code content
        prompt = renderer.render_prompt(prompt_template, code=code_content)

        # Call AI to get JSON metadata
        try:
            response_json_str = ai_service.ask_ai(prompt)
            node_metadata = json.loads(response_json_str)
        except Exception as e:
            print(f"Error processing {node_file.name}: {e}")
            continue

        node_jsons.append(node_metadata)

        print(f"Processed node: {node_metadata.get('id', node_file.stem.lower())}")

    # Write all node metadata to node_to_json.json as a list
    output_file = Path(__file__).parent / "node_to_json.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(node_jsons, f, indent=2)

    print(f"All node metadata saved to {output_file}")

if __name__ == "__main__":
    main()
