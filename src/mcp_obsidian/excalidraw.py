"""
Excalidraw note builder for Obsidian integration.

This module provides classes for building Excalidraw notes compatible with
the Obsidian Excalidraw plugin format.
"""

import json
import random
import string
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ExcalidrawElement:
    """Represents a single Excalidraw element with all required fields."""
    
    # Core fields
    id: str
    type: str
    x: float
    y: float
    width: float
    height: float
    
    # Style fields
    angle: float = 0
    strokeColor: str = "#1e1e1e"
    backgroundColor: str = "transparent"
    fillStyle: str = "solid"
    strokeWidth: int = 2
    strokeStyle: str = "solid"
    roughness: int = 1
    opacity: int = 100
    
    # Organizational fields
    groupIds: List[str] = field(default_factory=list)
    frameId: Optional[str] = None
    roundness: Optional[Dict[str, Any]] = None
    
    # Metadata fields
    seed: int = 1
    version: int = 1
    versionNonce: int = 1
    isDeleted: bool = False
    boundElements: List[Dict[str, str]] = field(default_factory=list)
    updated: int = 1
    link: Optional[str] = None
    locked: bool = False
    
    # Type-specific fields (populated based on element type)
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExcalidrawElement':
        """Create an ExcalidrawElement from a dictionary."""
        # Extract known fields
        known_fields = {
            'id', 'type', 'x', 'y', 'width', 'height', 'angle',
            'strokeColor', 'backgroundColor', 'fillStyle', 'strokeWidth',
            'strokeStyle', 'roughness', 'opacity', 'groupIds', 'frameId',
            'roundness', 'seed', 'version', 'versionNonce', 'isDeleted',
            'boundElements', 'updated', 'link', 'locked'
        }
        
        # Separate known and extra fields
        base_fields = {k: v for k, v in data.items() if k in known_fields}
        extra_fields = {k: v for k, v in data.items() if k not in known_fields}
        
        return cls(**base_fields, extra_fields=extra_fields)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the element to a dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "angle": self.angle,
            "strokeColor": self.strokeColor,
            "backgroundColor": self.backgroundColor,
            "fillStyle": self.fillStyle,
            "strokeWidth": self.strokeWidth,
            "strokeStyle": self.strokeStyle,
            "roughness": self.roughness,
            "opacity": self.opacity,
            "groupIds": self.groupIds,
            "frameId": self.frameId,
            "roundness": self.roundness,
            "seed": self.seed,
            "version": self.version,
            "versionNonce": self.versionNonce,
            "isDeleted": self.isDeleted,
            "boundElements": self.boundElements,
            "updated": self.updated,
            "link": self.link,
            "locked": self.locked,
        }
        
        # Add extra fields
        result.update(self.extra_fields)
        
        return result


class ExcalidrawElementProcessor:
    """Processes and enriches Excalidraw elements."""
    
    @staticmethod
    def generate_id(length: int = 8) -> str:
        """Generate a random alphanumeric ID."""
        return ''.join(random.choices(
            string.ascii_uppercase + string.ascii_lowercase + string.digits,
            k=length
        ))
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text by converting HTML breaks to newlines."""
        if not text:
            return text
        return text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    
    @classmethod
    def process_element(cls, element_data: Dict[str, Any]) -> List[ExcalidrawElement]:
        """
        Process a raw element, potentially creating additional elements.
        
        For elements with labels, creates separate text elements.
        Returns a list of processed elements.
        """
        element = ExcalidrawElement.from_dict(element_data)
        results = []
        
        # Handle elements with labels by creating separate text elements
        if "label" in element_data and element_data["label"]:
            label_text = cls._extract_label_text(element_data["label"])
            label_text = cls.sanitize_text(label_text)
            
            if label_text:
                text_element = cls._create_text_element_for_label(
                    element, label_text, element_data
                )
                # Update container's bound elements
                element.boundElements = [{"type": "text", "id": text_element.id}]
                results.extend([element, text_element])
            else:
                results.append(element)
        else:
            results.append(element)
        
        return results
    
    @staticmethod
    def _extract_label_text(label: Any) -> str:
        """Extract text from a label (dict or string)."""
        if isinstance(label, dict):
            return label.get("text", "")
        return str(label) if label else ""
    
    @classmethod
    def _create_text_element_for_label(
        cls,
        container: ExcalidrawElement,
        text: str,
        original_data: Dict[str, Any]
    ) -> ExcalidrawElement:
        """Create a text element for a container's label."""
        text_id = cls.generate_id()
        font_size = original_data.get("fontSize", 20)
        
        # Calculate text dimensions and position (centered in container)
        text_width = len(text) * font_size * 0.6
        text_height = font_size * 1.25
        text_x = container.x + (container.width - text_width) / 2
        text_y = container.y + (container.height - text_height) / 2
        
        return ExcalidrawElement(
            id=text_id,
            type="text",
            x=text_x,
            y=text_y,
            width=text_width,
            height=text_height,
            strokeColor=container.strokeColor,
            backgroundColor="transparent",
            extra_fields={
                "text": text,
                "fontSize": font_size,
                "fontFamily": original_data.get("fontFamily", 1),
                "textAlign": "center",
                "verticalAlign": "middle",
                "baseline": 18,
                "containerId": container.id,
                "originalText": text,
                "autoResize": True,
                "lineHeight": 1.25
            }
        )


class ExcalidrawTextExtractor:
    """Extracts text elements for the Text Elements section."""
    
    @staticmethod
    def extract_texts(elements: List[Dict[str, Any]]) -> List[str]:
        """Extract text content from elements with block reference IDs."""
        texts = []
        
        for element in elements:
            text_content = ExcalidrawTextExtractor._get_text_content(element)
            
            if text_content and text_content.strip():
                block_id = ExcalidrawElementProcessor.generate_id()
                texts.append(f"{text_content} ^{block_id}")
        
        return texts
    
    @staticmethod
    def _get_text_content(element: Dict[str, Any]) -> Optional[str]:
        """Get text content from an element."""
        # Check for direct text field
        if "text" in element and element.get("text"):
            return element["text"]
        
        # Check for label field
        if "label" in element:
            label = element["label"]
            if isinstance(label, dict):
                return label.get("text", "")
            elif isinstance(label, str):
                return label
        
        return None


class ExcalidrawNoteBuilder:
    """Builder for creating Excalidraw notes in Obsidian format."""
    
    DEFAULT_APP_STATE = {
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
    
    def __init__(self):
        self.elements: List[Dict[str, Any]] = []
        self.app_state: Dict[str, Any] = self.DEFAULT_APP_STATE.copy()
        self.frontmatter: Dict[str, Any] = {
            "excalidraw-plugin": "parsed",
            "tags": ["excalidraw"]
        }
        self.text_elements: str = ""
    
    def with_elements(self, elements: List[Dict[str, Any]]) -> 'ExcalidrawNoteBuilder':
        """Set the elements for the note."""
        # Process elements (handle labels, etc.)
        processor = ExcalidrawElementProcessor()
        processed = []
        
        for element_data in elements:
            processed.extend(processor.process_element(element_data))
        
        self.elements = [e.to_dict() for e in processed]
        return self
    
    def with_app_state(self, app_state: Optional[Dict[str, Any]]) -> 'ExcalidrawNoteBuilder':
        """Set custom app state."""
        if app_state:
            self.app_state = app_state
        return self
    
    def with_frontmatter(self, frontmatter: Dict[str, Any]) -> 'ExcalidrawNoteBuilder':
        """Merge additional frontmatter."""
        self.frontmatter.update(frontmatter)
        # Ensure tags are always present
        if "tags" not in self.frontmatter:
            self.frontmatter["tags"] = ["excalidraw"]
        return self
    
    def with_text_elements(self, text: str) -> 'ExcalidrawNoteBuilder':
        """Set custom text elements section."""
        self.text_elements = text
        return self
    
    def auto_extract_text_elements(self, elements: List[Dict[str, Any]]) -> 'ExcalidrawNoteBuilder':
        """Automatically extract text elements from the elements list."""
        extractor = ExcalidrawTextExtractor()
        texts = extractor.extract_texts(elements)
        self.text_elements = "\n\n".join(texts)
        return self
    
    def build(self) -> str:
        """Build the complete Excalidraw note content."""
        # Build frontmatter
        frontmatter = self._build_frontmatter()
        
        # Build Excalidraw JSON structure
        excalidraw_data = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
            "elements": self.elements,
            "appState": self.app_state,
            "files": {}
        }
        
        # Assemble note parts
        parts = [
            frontmatter,
            "",
            "==⚠ Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==",
            "",
            "# Excalidraw Data",
            "",
            "## Text Elements",
            self.text_elements,
            "%%",
            "## Drawing",
            "```json",
            json.dumps(excalidraw_data, indent="\t", ensure_ascii=False),
            "```",
            "%%"
        ]
        
        return "\n".join(parts)
    
    def _build_frontmatter(self) -> str:
        """Build the YAML frontmatter section."""
        lines = ["---"]
        
        for key, value in self.frontmatter.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, bool):
                lines.append(f"{key}: {str(value).lower()}")
            else:
                lines.append(f"{key}: {value}")
        
        lines.append("---")
        return "\n".join(lines)


def build_excalidraw_note(
    elements: List[Dict[str, Any]],
    app_state: Optional[Dict[str, Any]] = None,
    frontmatter: Optional[Dict[str, Any]] = None,
    text_elements: Optional[str] = None
) -> str:
    """
    Convenience function to build an Excalidraw note.
    
    Args:
        elements: List of Excalidraw element dictionaries
        app_state: Optional custom app state configuration
        frontmatter: Optional additional frontmatter metadata
        text_elements: Optional custom text elements section
    
    Returns:
        Complete Excalidraw note content as string
    """
    builder = ExcalidrawNoteBuilder()
    
    if frontmatter:
        builder.with_frontmatter(frontmatter)
    
    if app_state:
        builder.with_app_state(app_state)
    
    if text_elements:
        builder.with_text_elements(text_elements)
    else:
        builder.auto_extract_text_elements(elements)
    
    builder.with_elements(elements)
    
    return builder.build()
