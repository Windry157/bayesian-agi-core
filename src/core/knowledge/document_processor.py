#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档处理模块 - RAG核心能力
支持PDF、Word、Markdown等文档的解析和向量化
"""

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    from docx import Document
    HAS_PYDOCX = True
except ImportError:
    HAS_PYDOCX = False

class DocumentProcessor:
    """文档处理器"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """从PDF提取文本"""
        if not HAS_PYPDF2:
            raise ImportError("PyPDF2 not installed. Please install with: pip install PyPDF2")
        
        text = ""
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text.strip()
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """从Word文档提取文本"""
        if not HAS_PYDOCX:
            raise ImportError("python-docx not installed. Please install with: pip install python-docx")
        
        doc = Document(file_path)
        text = "\n\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
        return text.strip()
    
    @staticmethod
    def extract_text_from_markdown(file_path: str) -> str:
        """从Markdown文件提取文本"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """从TXT文件提取文本"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    
    @staticmethod
    def extract_text(file_path: str) -> str:
        """根据文件类型提取文本"""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            return DocumentProcessor.extract_text_from_pdf(file_path)
        elif ext == '.docx':
            return DocumentProcessor.extract_text_from_docx(file_path)
        elif ext == '.md':
            return DocumentProcessor.extract_text_from_markdown(file_path)
        elif ext == '.txt':
            return DocumentProcessor.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {ext}")
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        """将文本切分为小块"""
        chunks = []
        sentences = re.split(r'(?<=[。！？\n])', text)
        
        current_chunk = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence[:chunk_size]
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    @staticmethod
    def process_document(file_path: str, chunk_size: int = 500) -> Dict[str, Any]:
        """处理文档并返回结构化结果"""
        try:
            text = DocumentProcessor.extract_text(file_path)
            chunks = DocumentProcessor.chunk_text(text, chunk_size)
            
            return {
                'success': True,
                'file_name': Path(file_path).name,
                'file_type': Path(file_path).suffix.lower(),
                'total_chars': len(text),
                'total_chunks': len(chunks),
                'chunks': chunks
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }