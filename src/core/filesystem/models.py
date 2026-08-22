"""
文件系统数据模型
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

class FileType(Enum):
    """文件类型枚举"""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"

class PermissionLevel(Enum):
    """权限级别枚举"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

@dataclass
class DirectoryItem:
    """目录项"""
    name: str
    path: str
    type: FileType
    size: Optional[int] = None
    modified_at: Optional[datetime] = None
    permissions: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'path': self.path,
            'type': self.type.value,
            'size': self.size,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'permissions': self.permissions
        }

@dataclass
class FileContent:
    """文件内容"""
    path: str
    content: str
    encoding: str = "utf-8"
    size: int = 0
    modified_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            'path': self.path,
            'content': self.content,
            'encoding': self.encoding,
            'size': self.size,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None
        }

@dataclass
class FileMetadata:
    """文件元数据"""
    path: str
    name: str
    type: FileType
    size: int
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
    permissions: str
    owner: Optional[str] = None
    group: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'path': self.path,
            'name': self.name,
            'type': self.type.value,
            'size': self.size,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'accessed_at': self.accessed_at.isoformat(),
            'permissions': self.permissions,
            'owner': self.owner,
            'group': self.group
        }

@dataclass
class UserCredentials:
    """用户凭证"""
    username: str
    password_hash: str
    permissions: PermissionLevel
    allowed_paths: List[str] = field(default_factory=list)

@dataclass
class AccessToken:
    """访问令牌"""
    token: str
    username: str
    expires_at: datetime
    permissions: PermissionLevel
    
    def is_valid(self) -> bool:
        return datetime.now() < self.expires_at
