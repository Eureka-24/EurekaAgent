"""File Operations Tool - 文件操作工具

提供文件系统操作功能。
对应 PRD 5.2.3 和 SPEC 4.2.3

Note: 出于安全考虑，实际使用时应该限制可访问的目录范围
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog

logger = structlog.get_logger()


class FileOpsTool:
    """文件操作工具
    
    支持文件读写、目录操作等。
    """
    
    name = "file_ops"
    description = "执行文件系统操作，包括读写文件、创建目录、列出文件等"
    
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "操作类型: read, write, list, create_dir, exists, delete, info"
            },
            "path": {
                "type": "string",
                "description": "文件或目录路径"
            },
            "content": {
                "type": "string",
                "description": "写入文件的内容 (用于write操作)"
            },
            "encoding": {
                "type": "string",
                "description": "文件编码",
                "default": "utf-8"
            }
        },
        "required": ["operation", "path"]
    }
    
    def __init__(self, allowed_dirs: Optional[List[str]] = None):
        """初始化文件操作工具
        
        Args:
            allowed_dirs: 允许访问的目录列表，None表示不限制
        """
        self._allowed_dirs = allowed_dirs or []
    
    async def execute(
        self,
        operation: str,
        path: str,
        content: Optional[str] = None,
        encoding: str = "utf-8"
    ) -> str:
        """执行文件操作
        
        Args:
            operation: 操作类型
            path: 文件路径
            content: 写入内容
            encoding: 文件编码
            
        Returns:
            str: 操作结果
        """
        # 安全检查：确保路径在允许范围内
        if not self._is_path_allowed(path):
            return json.dumps({"error": "Access denied: path not in allowed directories"}, ensure_ascii=False)
        
        try:
            if operation == "read":
                return await self._read_file(path, encoding)
            elif operation == "write":
                return await self._write_file(path, content or "", encoding)
            elif operation == "list":
                return await self._list_dir(path)
            elif operation == "create_dir":
                return await self._create_dir(path)
            elif operation == "exists":
                return await self._exists(path)
            elif operation == "delete":
                return await self._delete(path)
            elif operation == "info":
                return await self._file_info(path)
            else:
                return json.dumps({"error": f"Unknown operation: {operation}"}, ensure_ascii=False)
                
        except Exception as e:
            logger.error("file_ops_error", operation=operation, path=path, error=str(e))
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def _is_path_allowed(self, path: str) -> bool:
        """检查路径是否在允许范围内"""
        if not self._allowed_dirs:
            return True
        
        abs_path = os.path.abspath(path)
        for allowed_dir in self._allowed_dirs:
            allowed_abs = os.path.abspath(allowed_dir)
            if abs_path.startswith(allowed_abs):
                return True
        return False
    
    async def _read_file(self, path: str, encoding: str) -> str:
        """读取文件内容"""
        file_path = Path(path)
        
        if not file_path.exists():
            return json.dumps({"error": f"File not found: {path}"}, ensure_ascii=False)
        
        if not file_path.is_file():
            return json.dumps({"error": f"Not a file: {path}"}, ensure_ascii=False)
        
        try:
            content = file_path.read_text(encoding=encoding)
            return json.dumps({
                "success": True,
                "path": path,
                "content": content,
                "size": len(content)
            }, ensure_ascii=False)
        except UnicodeDecodeError:
            return json.dumps({"error": f"Failed to decode file with {encoding} encoding"}, ensure_ascii=False)
    
    async def _write_file(self, path: str, content: str, encoding: str) -> str:
        """写入文件内容"""
        file_path = Path(path)
        
        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_text(content, encoding=encoding)
        
        return json.dumps({
            "success": True,
            "path": path,
            "bytes_written": len(content.encode(encoding))
        }, ensure_ascii=False)
    
    async def _list_dir(self, path: str) -> str:
        """列出目录内容"""
        dir_path = Path(path)
        
        if not dir_path.exists():
            return json.dumps({"error": f"Directory not found: {path}"}, ensure_ascii=False)
        
        if not dir_path.is_dir():
            return json.dumps({"error": f"Not a directory: {path}"}, ensure_ascii=False)
        
        entries = []
        for entry in dir_path.iterdir():
            stat = entry.stat()
            entries.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
        
        return json.dumps({
            "path": path,
            "entries": entries,
            "total": len(entries)
        }, ensure_ascii=False)
    
    async def _create_dir(self, path: str) -> str:
        """创建目录"""
        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        return json.dumps({
            "success": True,
            "path": path,
            "created": True
        }, ensure_ascii=False)
    
    async def _exists(self, path: str) -> str:
        """检查路径是否存在"""
        exists = Path(path).exists()
        
        return json.dumps({
            "path": path,
            "exists": exists
        }, ensure_ascii=False)
    
    async def _delete(self, path: str) -> str:
        """删除文件或目录"""
        file_path = Path(path)
        
        if not file_path.exists():
            return json.dumps({"error": f"Path not found: {path}"}, ensure_ascii=False)
        
        if file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        
        return json.dumps({
            "success": True,
            "path": path,
            "deleted": True
        }, ensure_ascii=False)
    
    async def _file_info(self, path: str) -> str:
        """获取文件/目录信息"""
        file_path = Path(path)
        
        if not file_path.exists():
            return json.dumps({"error": f"Path not found: {path}"}, ensure_ascii=False)
        
        stat = file_path.stat()
        
        info = {
            "path": path,
            "name": file_path.name,
            "type": "directory" if file_path.is_dir() else "file",
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime
        }
        
        return json.dumps(info, ensure_ascii=False)


# 创建默认实例（不限制访问，实际使用时请配置allowed_dirs）
_file_ops = FileOpsTool()


async def file_ops(
    operation: str,
    path: str,
    content: Optional[str] = None,
    encoding: str = "utf-8"
) -> str:
    """文件操作工具函数
    
    Usage:
        result = await file_ops("read", "path/to/file.txt")
        result = await file_ops("write", "path/to/file.txt", content="Hello")
        result = await file_ops("list", "path/to/dir")
    """
    return await _file_ops.execute(operation, path, content, encoding)