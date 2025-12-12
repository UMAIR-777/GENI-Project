import os
import importlib.util
import inspect
import json
from typing import Dict, Any, Set, List, Callable

class LanggraphHandler:
    """
    A utility class that provides methods for dynamically generating Python code:
    
    1. Generating dynamic wrapper functions from all Python files in a folder.
    2. Creating a GraphState TypedDict class based on JSON input.
    3. Generating a registry file that loads functions and classes from provided file paths.
    """

    @staticmethod
    def generate_wrapper_functions_dynamic(folder_paths: list[str,str], output_file_path: str, config_json: dict) -> None:
        """
        Scans the given folder for Python files and generates a dynamic wrapper for each target function
        as specified by the JSON configuration edges.

        For each edge with a valid target (ignoring special nodes like __start__ and __end__),
        a separate wrapper function is generated. If there are multiple edges for the same target,
        each edge’s mapping is used to build a distinct wrapper, and the wrapper function name is
        suffixed with an index to distinguish them.

        The generated wrapper dynamically imports the module containing the target function, extracts
        the parameters from the state using the mapping (or defaults to the parameter name), and then
        calls the function with those parameters.
        """
        # Build a dictionary mapping each target function (in lowercase) to a list of mapping dictionaries.
        # Each mapping corresponds to one edge in the configuration.
        target_edge_mappings = {}
        config = config_json.get("main", config_json)
        for edge in config.get("edges", []):
            target = edge.get("target")
            print(f"target:{target}")
            # Skip special nodes.
            if not target or (target.startswith("__") and target.endswith("__")):
                continue
            mapping = edge.get("mapping", {}) or {}
            # Convert target to lowercase
            target_edge_mappings.setdefault(target.lower(), []).append(mapping)

        wrappers_code = "# Auto-generated wrapper functions with dynamic imports\n\n"

        # loop over both avialabel_node_path and then tanet_nodes_path
        # TODO(Testing checking bucket on both paths)
        for folder_path in folder_paths:
            # Process each Python file in the folder.
            for filename in os.listdir(folder_path):
                if filename.endswith('.py') and filename != '__init__.py':
                    module_name = filename[:-3]  # Remove .py extension
                    file_path = os.path.join(folder_path, filename).replace("\\", "/")

                    # Dynamically import the module to inspect its functions.
                    spec = importlib.util.spec_from_file_location(module_name, os.path.join(folder_path, filename))
                    if spec is None or spec.loader is None:
                        continue
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Iterate over functions that are specified as targets in our JSON.
                    for func_name, func in inspect.getmembers(module, inspect.isfunction):
                        print(f"Found function: {func_name}")  # Debug print
                        # Compare using lowercase
                        print(f"target_edge_mappings:{target_edge_mappings}")
                        print(f"func_name:{func_name.lower()}")

                        if func_name.lower() not in target_edge_mappings:
                            continue

                        mapping_list = target_edge_mappings[func_name.lower()]
                        # Generate a wrapper for each mapping instance.
                        for idx, mapping in enumerate(mapping_list):
                            # Create a unique wrapper function name. If only one mapping, no index is added.
                            wrapper_suffix = "" if len(mapping_list) == 1 else f"_{idx+1}"
                            wrapper_func_name = f"{module_name}{wrapper_suffix}"

                            sig = inspect.signature(func)
                            params_code = ""
                            call_params = []
                            # Build code to extract each parameter from the state.
                            for param in sig.parameters.values():
                                if param.name in mapping:
                                    # Use the mapping value to extract the parameter.
                                    mapped_key = mapping[param.name]
                                    params_code += f'    {param.name} = state["{mapped_key}"]\n'
                                else:
                                    if param.default is inspect.Parameter.empty:
                                        params_code += f'    {param.name} = state["{param.name}"]\n'
                                    else:
                                        default_repr = repr(param.default)
                                        params_code += f'    {param.name} = state.get("{param.name}", {default_repr})\n'
                                call_params.append(param.name)
                            call_params_str = ", ".join(call_params)

                            # Generate the wrapper function code.
                            wrapper_func_code = (
                                f"def {wrapper_func_name}(state):\n"
                                f'    """Wrapper for the function {func_name} from module {module_name} with mapping {mapping}."""\n'
                                f"    import importlib.util\n"
                                f"    import os\n"
                                f"    module_name = '{module_name}'\n"
                                f"    file_path = os.path.join(r'{folder_path}', '{filename}').replace('\\\\', '/')\n"
                                f"    spec = importlib.util.spec_from_file_location(module_name, file_path)\n"
                                f"    module = importlib.util.module_from_spec(spec)\n"
                                f"    spec.loader.exec_module(module)\n"
                                f"    func = getattr(module, '{func_name}')\n"
                                f"{params_code}"
                                f"    return func({call_params_str})\n\n"
                            )
                            wrappers_code += wrapper_func_code

        # Write the generated wrapper functions to the output file.
        with open(output_file_path, "w") as f:
            f.write(wrappers_code)

        print(f"Dynamic wrapper functions generated and written to {output_file_path}")
        return output_file_path


    @staticmethod
    def extract_fields(nodes: List[Dict[str, Any]], field: str) -> Set[str]:
        """
        Extract unique keys from a list of node dictionaries for a given field 
        (for example, "inputs" or "output").

        Args:
            nodes: A list of node dictionaries.
            field: The key in each node whose subkeys are to be extracted.

        Returns:
            A set of unique keys found in the specified field.
        """
        fields = set()
        for node in nodes:
            if field in node and isinstance(node[field], dict):
                fields.update(node[field].keys())
        return fields

    @staticmethod
    def generate_class_code(input_fields: Set[str], output_fields: Set[str],
                            extra_input_fields: List[str] = None,
                            extra_output_fields: List[str] = None) -> str:
        """
        Generate the GraphState class definition code as a string, including both
        dynamic fields (extracted from JSON) and additional static fields.

        Args:
            input_fields: Set of input field names extracted from the JSON.
            output_fields: Set of output field names extracted from the JSON.
            extra_input_fields: Optional list of extra input field names to include.
            extra_output_fields: Optional list of extra output field names to include.

        Returns:
            A string containing the full class definition.
        """
        # Static fields that are always present.
        static_fields = [
            "messages: Annotated[Sequence[BaseMessage], add_messages]",
        ]

        # Set default extra fields if none provided.
        extra_input_fields = extra_input_fields or []
        extra_output_fields = extra_output_fields or []

        # Start building the class definition string.
        code = (
            "from typing import Sequence\n"
            "from typing_extensions import TypedDict\n"
            "from langchain_core.messages import BaseMessage\n"
            "from langgraph.graph.message import add_messages\n"
            "from typing import Annotated\n\n\n"
            "class GraphState(TypedDict):\n"
        )

        # Add static fields.
        for field in static_fields:
            code += f"    {field}\n"

        # Add dynamic input fields.
        code += "\n    # Inputs:\n"
        all_input_fields = set(input_fields) | set(extra_input_fields)
        for field in sorted(all_input_fields):
            code += f"    {field}: str\n"

        # Add dynamic output fields.
        code += "\n    # Outputs:\n"
        all_output_fields = set(output_fields) | set(extra_output_fields)
        for field in sorted(all_output_fields):
            code += f"    {field}: str\n"

        return code

    @staticmethod
    def generate_graph_state_file(json_data: Dict[str, Any], output_file_path: str,
                                  extra_input_fields: List[str] = None,
                                  extra_output_fields: List[str] = None) -> None:
        """
        Extract input and output keys from the provided JSON data and write a Python file
        that contains a dynamically generated GraphState TypedDict class.

        Args:
            json_data: JSON dictionary representing the workflow nodes.
            output_file: The path of the Python file to be written.
            extra_input_fields: Optional list of extra input field names.
            extra_output_fields: Optional list of extra output field names.
        """
        # Extract nodes from the JSON structure.
        nodes = json_data.get("main", {}).get("nodes", [])
        # Extract dynamic keys from the "inputs" and "output" fields.
        input_fields = LanggraphHandler.extract_fields(nodes, "inputs")
        output_fields = LanggraphHandler.extract_fields(nodes, "output")

        # Generate the GraphState class code.
        class_code = LanggraphHandler.generate_class_code(input_fields, output_fields,
                                                             extra_input_fields, extra_output_fields)

        # Write the generated class code to the output file.
        with open(output_file_path, "w") as f:
            f.write(class_code)

        print(f"GraphState class written to {output_file_path}")
        return output_file_path

    @staticmethod
    def generate_registry_from_file_paths(function_file_path: str, class_file_path: str,
                                            output_file_path: str = "function_registry.py") -> None:
        """
        Generates a registry file that dynamically loads a functions file and a classes file
        from the given file paths.

        The generated file uses a helper function to load the modules at runtime and creates
        two registries:
          - function_registry: mapping of function names to their corresponding functions.
          - class_registry: mapping of class names to their corresponding classes.
        
        It also provides two helper functions, get_function_reference and get_class_reference,
        for retrieving items by name.

        Args:
            function_file_path: File path to the Python file containing functions.
            class_file_path: File path to the Python file containing class definitions.
            output_file: File path where the generated registry file will be written.
        """
        lines = []
        lines.append("# Auto-generated registry file")
        lines.append("# This file dynamically loads functions and classes from provided file paths")
        lines.append("")
        lines.append("import importlib.util")
        lines.append("import os")
        lines.append("from typing import Callable")
        lines.append("")
        lines.append("def load_module_from_path(module_name: str, file_path: str):")
        lines.append("    spec = importlib.util.spec_from_file_location(module_name, file_path)")
        lines.append("    module = importlib.util.module_from_spec(spec)")
        lines.append("    spec.loader.exec_module(module)")
        lines.append("    return module")
        lines.append("")
        # Load the modules using the provided file paths.
        lines.append(f"functions_module = load_module_from_path('functions_module', r'{function_file_path}')")
        lines.append(f"classes_module = load_module_from_path('classes_module', r'{class_file_path}')")
        lines.append("")
        # Build the function registry.
        lines.append("function_registry = {}")
        lines.append("for name in dir(functions_module):")
        lines.append("    obj = getattr(functions_module, name)")
        lines.append("    # Ensure the object is callable and defined in our module")
        lines.append("    if callable(obj) and getattr(obj, '__module__', '') == 'functions_module':")
        lines.append("        function_registry[name] = obj")
        lines.append("")
        # Build the class registry.
        lines.append("class_registry = {}")
        lines.append("for name in dir(classes_module):")
        lines.append("    obj = getattr(classes_module, name)")
        lines.append("    # Ensure the object is a class and defined in our module")
        lines.append("    if isinstance(obj, type) and getattr(obj, '__module__', '') == 'classes_module':")
        lines.append("        class_registry[name] = obj")
        lines.append("")
        # Helper functions.
        lines.append("def get_function_reference(function_name: str) -> Callable:")
        lines.append("    return function_registry.get(function_name, lambda: None)")
        lines.append("")
        lines.append("def get_class_reference(class_name: str):")
        lines.append("    return class_registry.get(class_name)")
        lines.append("")
        
        # Write the assembled registry file.
        with open(output_file_path, "w") as f:
            f.write("\n".join(lines))
        
        print(f"Registry file '{output_file_path}' created successfully.")
        return output_file_path

# Example usage:
# LanggraphHandler.generate_wrapper_functions_dynamic("path/to/wrappers_folder", "all_wrappers_generated.py")
# json_data = json.load(open("workflow.json"))
# LanggraphHandler.generate_graph_state_file(json_data, "graph_state.py")
# LanggraphHandler.generate_registry_from_file_paths("all_wrappers_generated.py", "graph_state.py")
