from dataclasses import dataclass, field
from typing import List, Literal, Union

BlockType = Literal["text", "formula", "table"]  # ← добавили table

@dataclass
class Block:
    type: BlockType

@dataclass
class TextBlock(Block):
    content: str
    def __init__(self, content: str):
        self.type = "text"
        self.content = content

@dataclass
class FormulaBlock(Block):
    latex: str
    def __init__(self, latex: str):
        self.type = "formula"
        self.latex = latex

@dataclass
class TableBlock(Block): 
    latex: str 
    headers: List[str] = field(default_factory=list)  
    rows: List[List[str]] = field(default_factory=list)  
    
    def __init__(self, latex: str, headers: List[str] = None, rows: List[List[str]] = None):
        self.type = "table"
        self.latex = latex
        self.headers = headers or []
        self.rows = rows or []

@dataclass
class VariantDocument:
    number: int
    blocks: List[Union[TextBlock, FormulaBlock, TableBlock]] = field(default_factory=list)
    
    def to_plain_text(self) -> str:
        """Для обратной совместимости с БД"""
        result = []
        for block in self.blocks:
            if block.type == "text":
                result.append(block.content)
            elif block.type == "formula":
                result.append(f"\\({block.latex}\\)")
            elif block.type == "table":
                result.append(block.latex) 
        return "".join(result)