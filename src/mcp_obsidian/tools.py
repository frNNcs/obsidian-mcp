from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import json
import os
from . import obsidian

api_key = os.getenv("OBSIDIAN_API_KEY", "")
obsidian_host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")

if api_key == "":
    raise ValueError(f"OBSIDIAN_API_KEY environment variable required. Working directory: {os.getcwd()}")

TOOL_LIST_FILES_IN_VAULT = "obsidian_list_files_in_vault"
TOOL_LIST_FILES_IN_DIR = "obsidian_list_files_in_dir"

class ToolHandler():
    def __init__(self, tool_name: str):
        self.name = tool_name

    def get_tool_description(self) -> Tool:
        raise NotImplementedError()

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError()
    
class ListFilesInVaultToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_VAULT)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories in the root directory of your Obsidian vault.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        files = api.list_files_in_vault()

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )
        ]
    
class ListFilesInDirToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_DIR)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories that exist in a specific Obsidian directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dirpath": {
                        "type": "string",
                        "description": "Path to list files from (relative to your vault root). Note that empty directories will not be returned."
                    },
                },
                "required": ["dirpath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:

        if "dirpath" not in args:
            raise RuntimeError("dirpath argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        files = api.list_files_in_dir(args["dirpath"])

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )
        ]
    
class GetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the content of a single file in your vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the relevant file (relative to your vault root).",
                        "format": "path"
                    },
                },
                "required": ["filepath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        content = api.get_file_contents(args["filepath"])

        return [
            TextContent(
                type="text",
                text=json.dumps(content, indent=2)
            )
        ]
    
class SearchToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_simple_search")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="""Simple search for documents matching a specified text query across all files in the vault. 
            Use this tool when you want to do a simple text search""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to a simple search for in the vault."
                    },
                    "context_length": {
                        "type": "integer",
                        "description": "How much context to return around the matching string (default: 100)",
                        "default": 100
                    }
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "query" not in args:
            raise RuntimeError("query argument missing in arguments")

        context_length = args.get("context_length", 100)
        
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.search(args["query"], context_length)
        
        formatted_results = []
        for result in results:
            formatted_matches = []
            for match in result.get('matches', []):
                context = match.get('context', '')
                match_pos = match.get('match', {})
                start = match_pos.get('start', 0)
                end = match_pos.get('end', 0)
                
                formatted_matches.append({
                    'context': context,
                    'match_position': {'start': start, 'end': end}
                })
                
            formatted_results.append({
                'filename': result.get('filename', ''),
                'score': result.get('score', 0),
                'matches': formatted_matches
            })

        return [
            TextContent(
                type="text",
                text=json.dumps(formatted_results, indent=2)
            )
        ]
    
class AppendContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_append_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Append content to a new or existing file in the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to append to the file"
                   }
               },
               "required": ["filepath", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args or "content" not in args:
           raise RuntimeError("filepath and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.append_content(args.get("filepath", ""), args["content"])

       return [
           TextContent(
               type="text",
               text=f"Successfully appended content to {args['filepath']}"
           )
       ]
   
class PatchContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_patch_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Insert content into an existing note relative to a heading, block reference, or frontmatter field.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "operation": {
                       "type": "string",
                       "description": "Operation to perform (append, prepend, or replace)",
                       "enum": ["append", "prepend", "replace"]
                   },
                   "target_type": {
                       "type": "string",
                       "description": "Type of target to patch",
                       "enum": ["heading", "block", "frontmatter"]
                   },
                   "target": {
                       "type": "string", 
                       "description": "Target identifier (heading path, block reference, or frontmatter field)"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to insert"
                   }
               },
               "required": ["filepath", "operation", "target_type", "target", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if not all(k in args for k in ["filepath", "operation", "target_type", "target", "content"]):
           raise RuntimeError("filepath, operation, target_type, target and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.patch_content(
           args.get("filepath", ""),
           args.get("operation", ""),
           args.get("target_type", ""),
           args.get("target", ""),
           args.get("content", "")
       )

       return [
           TextContent(
               type="text",
               text=f"Successfully patched content in {args['filepath']}"
           )
       ]
       
class PutContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_put_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Create a new file in your vault or update the content of an existing one in your vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the relevant file (relative to your vault root)",
                       "format": "path"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content of the file you would like to upload"
                   }
               },
               "required": ["filepath", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args or "content" not in args:
           raise RuntimeError("filepath and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.put_content(args.get("filepath", ""), args["content"])

       return [
           TextContent(
               type="text",
               text=f"Successfully uploaded content to {args['filepath']}"
           )
       ]
   

class DeleteFileToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_delete_file")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Delete a file or directory from the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file or directory to delete (relative to vault root)",
                       "format": "path"
                   },
                   "confirm": {
                       "type": "boolean",
                       "description": "Confirmation to delete the file (must be true)",
                       "default": False
                   }
               },
               "required": ["filepath", "confirm"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args:
           raise RuntimeError("filepath argument missing in arguments")
       
       if not args.get("confirm", False):
           raise RuntimeError("confirm must be set to true to delete a file")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.delete_file(args["filepath"])

       return [
           TextContent(
               type="text",
               text=f"Successfully deleted {args['filepath']}"
           )
       ]
   
class ComplexSearchToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_complex_search")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="""Complex search for documents using a JsonLogic query. 
           Supports standard JsonLogic operators plus 'glob' and 'regexp' for pattern matching. Results must be non-falsy.

           Use this tool when you want to do a complex search, e.g. for all documents with certain tags etc.
           ALWAYS follow query syntax in examples.

           Examples
            1. Match all markdown files
            {"glob": ["*.md", {"var": "path"}]}

            2. Match all markdown files with 1221 substring inside them
            {
              "and": [
                { "glob": ["*.md", {"var": "path"}] },
                { "regexp": [".*1221.*", {"var": "content"}] }
              ]
            }

            3. Match all markdown files in Work folder containing name Keaton
            {
              "and": [
                { "glob": ["*.md", {"var": "path"}] },
                { "regexp": [".*Work.*", {"var": "path"}] },
                { "regexp": ["Keaton", {"var": "content"}] }
              ]
            }
           """,
           inputSchema={
               "type": "object",
               "properties": {
                   "query": {
                       "type": "object",
                       "description": "JsonLogic query object. ALWAYS follow query syntax in examples. \
                            Example 1: {\"glob\": [\"*.md\", {\"var\": \"path\"}]} matches all markdown files \
                            Example 2: {\"and\": [{\"glob\": [\"*.md\", {\"var\": \"path\"}]}, {\"regexp\": [\".*1221.*\", {\"var\": \"content\"}]}]} matches all markdown files with 1221 substring inside them \
                            Example 3: {\"and\": [{\"glob\": [\"*.md\", {\"var\": \"path\"}]}, {\"regexp\": [\".*Work.*\", {\"var\": \"path\"}]}, {\"regexp\": [\"Keaton\", {\"var\": \"content\"}]}]} matches all markdown files in Work folder containing name Keaton \
                        "
                   }
               },
               "required": ["query"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "query" not in args:
           raise RuntimeError("query argument missing in arguments")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       results = api.search_json(args.get("query", ""))

       return [
           TextContent(
               type="text",
               text=json.dumps(results, indent=2)
           )
       ]

class BatchGetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_batch_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the contents of multiple files in your vault, concatenated with headers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepaths": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Path to a file (relative to your vault root)",
                            "format": "path"
                        },
                        "description": "List of file paths to read"
                    },
                },
                "required": ["filepaths"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepaths" not in args:
            raise RuntimeError("filepaths argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_batch_file_contents(args["filepaths"])

        return [
            TextContent(
                type="text",
                text=content
            )
        ]

class PeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_periodic_note")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get current periodic note for the specified period.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "The period type (daily, weekly, monthly, quarterly, yearly)",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                    },
                    "type": {
                        "type": "string",
                        "description": "The type of data to get ('content' or 'metadata'). 'content' returns just the content in Markdown format. 'metadata' includes note metadata (including paths, tags, etc.) and the content.",
                        "default": "content",
                        "enum": ["content", "metadata"]
                    }
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")

        period = args["period"]
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise RuntimeError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")
        
        type = args["type"] if "type" in args else "content"
        valid_types = ["content", "metadata"]
        if type not in valid_types:
            raise RuntimeError(f"Invalid type: {type}. Must be one of: {', '.join(valid_types)}")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_periodic_note(period,type)

        return [
            TextContent(
                type="text",
                text=content
            )
        ]
        
class RecentPeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_periodic_notes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get most recent periodic notes for the specified period type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "The period type (daily, weekly, monthly, quarterly, yearly)",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Whether to include note content (default: false)",
                        "default": False
                    }
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")

        period = args["period"]
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise RuntimeError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")

        limit = args.get("limit", 5)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")
            
        include_content = args.get("include_content", False)
        if not isinstance(include_content, bool):
            raise RuntimeError(f"Invalid include_content: {include_content}. Must be a boolean")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_periodic_notes(period, limit, include_content)

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]
        
class RecentChangesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_changes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get recently modified files in the vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of files to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "days": {
                        "type": "integer",
                        "description": "Only include files modified within this many days (default: 90)",
                        "default": 90,
                        "minimum": 1
                    }
                },
                "required": []
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        limit = args.get("limit", 10)
        days = args.get("days", 90)
        
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_changes(limit, days)
        
        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]


class SaveExcalidrawToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_save_excalidraw")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Save Excalidraw elements to an Obsidian note using the Excalidraw plugin template format. Takes JSON elements from Excalidraw MCP query and creates/updates an Obsidian Excalidraw note.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file (relative to vault root). Should end with .excalidraw.md",
                        "format": "path"
                    },
                    "elements": {
                        "type": "array",
                        "description": "Array of Excalidraw element objects to save. This is the 'elements' array from Excalidraw.",
                        "items": {
                            "type": "object"
                        }
                    },
                    "appState": {
                        "type": "object",
                        "description": "Optional Excalidraw appState configuration. If not provided, sensible defaults will be used.",
                        "default": None
                    },
                    "frontmatter": {
                        "type": "object",
                        "description": "Optional frontmatter metadata for the note (e.g., tags, references). Will be merged with required Excalidraw frontmatter.",
                        "default": {}
                    },
                    "text_elements": {
                        "type": "string",
                        "description": "Optional text content to add in the Text Elements section of the Excalidraw note.",
                        "default": ""
                    }
                },
                "required": ["filepath", "elements"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepath" not in args or "elements" not in args:
            raise ValueError("filepath and elements are required")

        filepath = args["filepath"]
        elements = args["elements"]
        appState = args.get("appState")
        frontmatter = args.get("frontmatter", {})
        text_elements = args.get("text_elements", "")

        # Ensure filepath ends with .excalidraw.md
        if not filepath.endswith(".excalidraw.md"):
            if filepath.endswith(".md"):
                filepath = filepath.replace(".md", ".excalidraw.md")
            else:
                filepath = f"{filepath}.excalidraw.md"

        # Build the Excalidraw note content
        content = self._build_excalidraw_note(elements, appState, frontmatter, text_elements)

        # Save to Obsidian
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.put_content(filepath, content)

        return [
            TextContent(
                type="text",
                text=f"Successfully saved Excalidraw drawing to {filepath} with {len(elements)} elements"
            )
        ]

    def _build_excalidraw_note(self, elements: list, appState: dict | None, frontmatter: dict, text_elements: str) -> str:
        """Build the complete Excalidraw note content following Obsidian Excalidraw plugin format."""
        
        # Merge frontmatter with required Excalidraw fields
        final_frontmatter = {
            "excalidraw-plugin": "parsed",
            "tags": frontmatter.get("tags", ["excalidraw"]),
            **frontmatter
        }

        # Build default appState if not provided
        if appState is None:
            appState = {
                "theme": "light",
                "viewBackgroundColor": "#ffffff",
                "currentItemStrokeColor": "#1e1e1e",
                "currentItemBackgroundColor": "transparent",
                "currentItemFillStyle": "solid",
                "currentItemStrokeWidth": 2,
                "currentItemStrokeStyle": "solid",
                "currentItemRoughness": 1,
                "currentItemOpacity": 100,
                "currentItemFontFamily": 1,
                "currentItemFontSize": 20,
                "currentItemTextAlign": "left",
                "currentItemStartArrowhead": None,
                "currentItemEndArrowhead": "arrow",
                "scrollX": 0,
                "scrollY": 0,
                "zoom": {"value": 1},
                "currentItemRoundness": "round",
                "gridSize": None,
                "gridColor": {
                    "Bold": "#C9C9C9FF",
                    "Regular": "#EDEDEDFF"
                },
                "currentStrokeOptions": None,
                "previousGridSize": None,
                "frameRendering": {
                    "enabled": True,
                    "clip": True,
                    "name": True,
                    "outline": True
                }
            }

        # Extract text elements from the elements array
        # Look for elements with 'text' field or elements with 'label' containing text
        extracted_texts = []
        if not text_elements:
            for element in elements:
                text_content = None
                
                # Check for direct text field (for text elements)
                if "text" in element and element.get("text"):
                    text_content = element["text"]
                # Check for label field (for shapes with labels like rectangles, ellipses, etc.)
                elif "label" in element and isinstance(element["label"], dict):
                    text_content = element["label"].get("text", "")
                elif "label" in element and isinstance(element["label"], str):
                    text_content = element["label"]
                
                # Add to extracted texts if we found any text
                if text_content and text_content.strip():
                    # Generate a unique block reference ID (8 characters alphanumeric)
                    import random
                    import string
                    block_id = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=8))
                    extracted_texts.append(f"{text_content} ^{block_id}")
            
            # Join all extracted texts with double newlines (blank line between each)
            text_elements = "\n\n".join(extracted_texts) if extracted_texts else ""

        # Ensure all elements have required Excalidraw fields and create text elements for labels
        processed_elements = []
        import random
        import string
        
        for element in elements:
            # Create a copy with all required fields
            element_id = element.get("id", "")
            processed_element = {
                "id": element_id,
                "type": element.get("type", ""),
                "x": element.get("x", 0),
                "y": element.get("y", 0),
                "width": element.get("width", 0),
                "height": element.get("height", 0),
                "angle": element.get("angle", 0),
                "strokeColor": element.get("strokeColor", "#1e1e1e"),
                "backgroundColor": element.get("backgroundColor", "transparent"),
                "fillStyle": element.get("fillStyle", "solid"),
                "strokeWidth": element.get("strokeWidth", 2),
                "strokeStyle": element.get("strokeStyle", "solid"),
                "roughness": element.get("roughness", 1),
                "opacity": element.get("opacity", 100),
                "groupIds": element.get("groupIds", []),
                "frameId": element.get("frameId", None),
                "roundness": element.get("roundness", None),
                "seed": element.get("seed", 1),
                "version": element.get("version", 1),
                "versionNonce": element.get("versionNonce", 1),
                "isDeleted": element.get("isDeleted", False),
                "boundElements": element.get("boundElements", []),
                "updated": element.get("updated", 1),
                "link": element.get("link", None),
                "locked": element.get("locked", False),
            }
            
            # Add type-specific fields
            if element.get("type") == "arrow" or element.get("type") == "line":
                processed_element["points"] = element.get("points", [[0, 0], [element.get("width", 100), element.get("height", 0)]])
                processed_element["lastCommittedPoint"] = element.get("lastCommittedPoint", None)
                processed_element["startBinding"] = element.get("startBinding", None)
                processed_element["endBinding"] = element.get("endBinding", None)
                processed_element["startArrowhead"] = element.get("startArrowhead", None)
                processed_element["endArrowhead"] = element.get("endArrowhead", "arrow")
            
            # Handle labels by creating separate text elements
            if "label" in element and element["label"]:
                label_text = element["label"].get("text", "") if isinstance(element["label"], dict) else element["label"]
                
                # Replace HTML <br> tags with actual newlines
                if label_text:
                    label_text = label_text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
                
                if label_text:
                    # Generate unique ID for text element
                    text_id = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=8))
                    
                    # Calculate text position (centered in the container)
                    font_size = element.get("fontSize", 20)
                    # Approximate text width (rough estimate)
                    text_width = len(label_text) * font_size * 0.6
                    text_height = font_size * 1.25
                    
                    text_x = element.get("x", 0) + (element.get("width", 0) - text_width) / 2
                    text_y = element.get("y", 0) + (element.get("height", 0) - text_height) / 2
                    
                    # Add boundElement to container
                    processed_element["boundElements"] = [{"type": "text", "id": text_id}]
                    
                    # Create text element
                    text_element = {
                        "id": text_id,
                        "type": "text",
                        "x": text_x,
                        "y": text_y,
                        "width": text_width,
                        "height": text_height,
                        "angle": 0,
                        "strokeColor": element.get("strokeColor", "#1e1e1e"),
                        "backgroundColor": "transparent",
                        "fillStyle": "solid",
                        "strokeWidth": 2,
                        "strokeStyle": "solid",
                        "roughness": 1,
                        "opacity": 100,
                        "groupIds": [],
                        "frameId": None,
                        "roundness": None,
                        "seed": 1,
                        "version": 1,
                        "versionNonce": 1,
                        "isDeleted": False,
                        "boundElements": [],
                        "updated": 1,
                        "link": None,
                        "locked": False,
                        "text": label_text,
                        "fontSize": font_size,
                        "fontFamily": element.get("fontFamily", 1),
                        "textAlign": "center",
                        "verticalAlign": "middle",
                        "containerId": element_id,
                        "originalText": label_text,
                        "autoResize": True,
                        "lineHeight": 1.25
                    }
                    
                    # Add both container and text elements
                    processed_elements.append(processed_element)
                    processed_elements.append(text_element)
                else:
                    processed_elements.append(processed_element)
            # Handle direct text elements
            elif "text" in element:
                processed_element["text"] = element["text"]
                processed_element["fontSize"] = element.get("fontSize", 20)
                processed_element["fontFamily"] = element.get("fontFamily", 1)
                processed_element["textAlign"] = element.get("textAlign", "left")
                processed_element["verticalAlign"] = element.get("verticalAlign", "top")
                processed_element["baseline"] = element.get("baseline", 18)
                processed_element["containerId"] = element.get("containerId", None)
                processed_element["originalText"] = element.get("originalText", element["text"])
                processed_element["autoResize"] = element.get("autoResize", True)
                processed_element["lineHeight"] = element.get("lineHeight", 1.25)
                processed_elements.append(processed_element)
            else:
                processed_elements.append(processed_element)

        # Build the Excalidraw JSON structure
        excalidraw_data = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
            "elements": processed_elements,
            "appState": appState,
            "files": {}
        }

        # Build frontmatter YAML
        frontmatter_lines = ["---"]
        for key, value in final_frontmatter.items():
            if isinstance(value, list):
                frontmatter_lines.append(f"{key}:")
                for item in value:
                    frontmatter_lines.append(f"  - {item}")
            elif isinstance(value, bool):
                frontmatter_lines.append(f"{key}: {str(value).lower()}")
            else:
                frontmatter_lines.append(f"{key}: {value}")
        frontmatter_lines.append("---")
        
        # Build complete note content
        note_parts = [
            "\n".join(frontmatter_lines),
            "",
            "==⚠ Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==",
            "",
            "# Excalidraw Data",
            "",
            "## Text Elements",
            text_elements if text_elements else "",
            "%%",
            "## Drawing",
            "```json",
            json.dumps(excalidraw_data, indent="\t", ensure_ascii=False),
            "```",
            "%%"
        ]

        return "\n".join(note_parts)
