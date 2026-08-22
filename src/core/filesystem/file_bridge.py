"""
文件系统桥接器 - 提供安全的文件系统访问接口
"""
import os
import stat
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from .models import DirectoryItem, FileContent, FileMetadata, FileType, PermissionLevel
from .auth_manager import AuthManager, AuthConfig
import logging

logger = logging.getLogger(__name__)

@dataclass
class FileBridgeConfig:
    """文件桥接配置"""
    root_path: str = "./data"
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = field(default_factory=list)
    denied_patterns: List[str] = field(default_factory=lambda: ["..", "/../"])
    enable_auth: bool = True
    allow_anonymous_read: bool = False

class FileBridge:
    """文件系统桥接器"""
    
    def __init__(self, config: Optional[FileBridgeConfig] = None):
        self.config = config or FileBridgeConfig()
        self.auth_manager = AuthManager(AuthConfig(allow_anonymous_read=self.config.allow_anonymous_read))
        self._ensure_root_path()
        
    def _ensure_root_path(self):
        """确保根目录存在"""
        os.makedirs(self.config.root_path, exist_ok=True)
        logger.info(f"✅ 文件系统桥接器初始化完成，根目录: {self.config.root_path}")
        
    def _sanitize_path(self, path: str) -> Optional[str]:
        """路径安全检查"""
        path = path.lstrip('/')
        
        for pattern in self.config.denied_patterns:
            if pattern in path:
                logger.warning(f"❌ 路径包含非法模式: {path}")
                return None
                
        full_path = os.path.abspath(os.path.join(self.config.root_path, path))
        
        if not full_path.startswith(os.path.abspath(self.config.root_path)):
            logger.warning(f"❌ 路径越界: {path}")
            return None
            
        return full_path
        
    def _check_permission(self, token: str, path: str, permission: PermissionLevel) -> bool:
        """检查权限"""
        if not self.config.enable_auth:
            return True
        return self.auth_manager.check_permission(token, path, permission)
        
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """用户认证"""
        return self.auth_manager.authenticate(username, password)
        
    def list_directories(self, path: str = "", token: str = "") -> List[DirectoryItem]:
        """列出目录内容"""
        if not self._check_permission(token, path, PermissionLevel.READ):
            raise PermissionError("无权访问")
            
        sanitized_path = self._sanitize_path(path)
        if not sanitized_path:
            raise ValueError("无效路径")
            
        if not os.path.isdir(sanitized_path):
            raise NotADirectoryError(f"不是目录: {path}")
            
        items: List[DirectoryItem] = []
        for entry in os.listdir(sanitized_path):
            entry_path = os.path.join(sanitized_path, entry)
            rel_path = os.path.relpath(entry_path, self.config.root_path).replace(os.sep, '/')
            
            try:
                stat_info = os.stat(entry_path)
                
                if os.path.isdir(entry_path):
                    item_type = FileType.DIRECTORY
                    size = None
                elif os.path.islink(entry_path):
                    item_type = FileType.SYMLINK
                    size = stat_info.st_size
                else:
                    item_type = FileType.FILE
                    size = stat_info.st_size
                    
                modified_at = datetime.fromtimestamp(stat_info.st_mtime)
                permissions = self._get_permissions_string(stat_info.st_mode)
                
                items.append(DirectoryItem(
                    name=entry,
                    path=rel_path,
                    type=item_type,
                    size=size,
                    modified_at=modified_at,
                    permissions=permissions
                ))
            except Exception as e:
                logger.warning(f"⚠️ 无法读取条目 {entry}: {e}")
                continue
                
        items.sort(key=lambda x: (x.type.value, x.name.lower()))
        return items
        
    def _get_permissions_string(self, mode: int) -> str:
        """获取权限字符串"""
        perms = []
        perms.append('d' if stat.S_ISDIR(mode) else '-')
        perms.append('r' if mode & stat.S_IRUSR else '-')
        perms.append('w' if mode & stat.S_IWUSR else '-')
        perms.append('x' if mode & stat.S_IXUSR else '-')
        perms.append('r' if mode & stat.S_IRGRP else '-')
        perms.append('w' if mode & stat.S_IWGRP else '-')
        perms.append('x' if mode & stat.S_IXGRP else '-')
        perms.append('r' if mode & stat.S_IROTH else '-')
        perms.append('w' if mode & stat.S_IWOTH else '-')
        perms.append('x' if mode & stat.S_IXOTH else '-')
        return ''.join(perms)
        
    def read_file_content(self, path: str, token: str = "") -> FileContent:
        """读取文件内容"""
        if not self._check_permission(token, path, PermissionLevel.READ):
            raise PermissionError("无权读取")
            
        sanitized_path = self._sanitize_path(path)
        if not sanitized_path:
            raise ValueError("无效路径")
            
        if not os.path.isfile(sanitized_path):
            raise FileNotFoundError(f"文件不存在: {path}")
            
        stat_info = os.stat(sanitized_path)
        if stat_info.st_size > self.config.max_file_size_bytes:
            raise ValueError(f"文件过大，最大允许 {self.config.max_file_size_bytes // (1024*1024)}MB")
            
        if self.config.allowed_extensions:
            ext = os.path.splitext(path)[1].lower()
            if ext and ext not in self.config.allowed_extensions:
                raise ValueError(f"不支持的文件类型: {ext}")
                
        try:
            with open(sanitized_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            modified_at = datetime.fromtimestamp(stat_info.st_mtime)
            
            return FileContent(
                path=path,
                content=content,
                encoding='utf-8',
                size=stat_info.st_size,
                modified_at=modified_at
            )
        except UnicodeDecodeError:
            with open(sanitized_path, 'rb') as f:
                content = f.read().hex()
            return FileContent(
                path=path,
                content=content,
                encoding='hex',
                size=stat_info.st_size,
                modified_at=modified_at
            )
            
    def write_file_content(self, path: str, content: str, token: str = "", encoding: str = "utf-8") -> bool:
        """写入文件内容"""
        if not self._check_permission(token, path, PermissionLevel.WRITE):
            raise PermissionError("无权写入")
            
        sanitized_path = self._sanitize_path(path)
        if not sanitized_path:
            raise ValueError("无效路径")
            
        if self.config.allowed_extensions:
            ext = os.path.splitext(path)[1].lower()
            if ext and ext not in self.config.allowed_extensions:
                raise ValueError(f"不支持的文件类型: {ext}")
                
        content_bytes = content.encode(encoding) if encoding == 'utf-8' else bytes.fromhex(content)
        if len(content_bytes) > self.config.max_file_size_bytes:
            raise ValueError(f"内容过大，最大允许 {self.config.max_file_size_bytes // (1024*1024)}MB")
            
        try:
            os.makedirs(os.path.dirname(sanitized_path), exist_ok=True)
            with open(sanitized_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"✅ 写入文件: {path}")
            return True
        except Exception as e:
            logger.error(f"❌ 写入文件失败 {path}: {e}")
            raise
            
    def get_file_metadata(self, path: str, token: str = "") -> FileMetadata:
        """获取文件元数据"""
        if not self._check_permission(token, path, PermissionLevel.READ):
            raise PermissionError("无权访问")
            
        sanitized_path = self._sanitize_path(path)
        if not sanitized_path:
            raise ValueError("无效路径")
            
        if not os.path.exists(sanitized_path):
            raise FileNotFoundError(f"文件/目录不存在: {path}")
            
        stat_info = os.stat(sanitized_path)
        
        if os.path.isdir(sanitized_path):
            file_type = FileType.DIRECTORY
        elif os.path.islink(sanitized_path):
            file_type = FileType.SYMLINK
        else:
            file_type = FileType.FILE
            
        return FileMetadata(
            path=path,
            name=os.path.basename(path),
            type=file_type,
            size=stat_info.st_size,
            created_at=datetime.fromtimestamp(stat_info.st_ctime),
            modified_at=datetime.fromtimestamp(stat_info.st_mtime),
            accessed_at=datetime.fromtimestamp(stat_info.st_atime),
            permissions=self._get_permissions_string(stat_info.st_mode),
            owner=None,
            group=None
        )
        
    def create_directory(self, path: str, token: str = "") -> bool:
        """创建目录"""
        if not self._check_permission(token, path, PermissionLevel.WRITE):
            raise PermissionError("无权创建")
            
        sanitized_path = self._sanitize_path(path)
        if not sanitized_path:
            raise ValueError("无效路径")
            
        try:
            os.makedirs(sanitized_path, exist_ok=True)
            logger.info(f"✅ 创建目录: {path}")
            return True
        except Exception as e:
            logger.error(f"❌ 创建目录失败 {path}: {e}")
            raise
            
    def delete_file(self, path: str, token: str = "") -> bool:
        """删除文件"""
        if not self._check_permission(token, path, PermissionLevel.WRITE):
            raise PermissionError("无权删除")
            
        sanitized_path = self._sanitize_path(path)
        if not sanitized_path:
            raise ValueError("无效路径")
            
        if not os.path.exists(sanitized_path):
            raise FileNotFoundError(f"文件/目录不存在: {path}")
            
        try:
            if os.path.isdir(sanitized_path):
                shutil.rmtree(sanitized_path)
            else:
                os.remove(sanitized_path)
            logger.info(f"✅ 删除: {path}")
            return True
        except Exception as e:
            logger.error(f"❌ 删除失败 {path}: {e}")
            raise
            
    def rename_file(self, old_path: str, new_path: str, token: str = "") -> bool:
        """重命名文件/目录"""
        if not self._check_permission(token, old_path, PermissionLevel.WRITE):
            raise PermissionError("无权操作")
            
        sanitized_old = self._sanitize_path(old_path)
        sanitized_new = self._sanitize_path(new_path)
        
        if not sanitized_old or not sanitized_new:
            raise ValueError("无效路径")
            
        if not os.path.exists(sanitized_old):
            raise FileNotFoundError(f"源文件不存在: {old_path}")
            
        try:
            os.rename(sanitized_old, sanitized_new)
            logger.info(f"✅ 重命名: {old_path} -> {new_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 重命名失败 {old_path} -> {new_path}: {e}")
            raise
            
    def copy_file(self, source_path: str, dest_path: str, token: str = "") -> bool:
        """复制文件/目录"""
        if not self._check_permission(token, source_path, PermissionLevel.READ):
            raise PermissionError("无权读取源文件")
        if not self._check_permission(token, dest_path, PermissionLevel.WRITE):
            raise PermissionError("无权写入目标路径")
            
        sanitized_source = self._sanitize_path(source_path)
        sanitized_dest = self._sanitize_path(dest_path)
        
        if not sanitized_source or not sanitized_dest:
            raise ValueError("无效路径")
            
        if not os.path.exists(sanitized_source):
            raise FileNotFoundError(f"源文件不存在: {source_path}")
            
        try:
            if os.path.isdir(sanitized_source):
                shutil.copytree(sanitized_source, sanitized_dest)
            else:
                shutil.copy2(sanitized_source, sanitized_dest)
            logger.info(f"✅ 复制: {source_path} -> {dest_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 复制失败 {source_path} -> {dest_path}: {e}")
            raise
            
    def exists(self, path: str, token: str = "") -> bool:
        """检查路径是否存在"""
        if not self._check_permission(token, path, PermissionLevel.READ):
            return False
            
        sanitized_path = self._sanitize_path(path)
        if not sanitized_path:
            return False
            
        return os.path.exists(sanitized_path)
        
    def get_tree(self, path: str = "", depth: int = 3, token: str = "") -> Dict[str, Any]:
        """获取目录树结构"""
        if not self._check_permission(token, path, PermissionLevel.READ):
            raise PermissionError("无权访问")
            
        sanitized_path = self._sanitize_path(path)
        if not sanitized_path:
            raise ValueError("无效路径")
            
        return self._build_tree(sanitized_path, depth, token)
        
    def _build_tree(self, base_path: str, depth: int, token: str) -> Dict[str, Any]:
        """递归构建目录树"""
        result = {
            'name': os.path.basename(base_path) or '/',
            'path': os.path.relpath(base_path, self.config.root_path).replace(os.sep, '/') or '/',
            'type': 'directory' if os.path.isdir(base_path) else 'file',
            'children': []
        }
        
        if os.path.isdir(base_path) and depth > 0:
            for entry in sorted(os.listdir(base_path)):
                entry_path = os.path.join(base_path, entry)
                try:
                    result['children'].append(self._build_tree(entry_path, depth - 1, token))
                except Exception:
                    continue
                    
        return result
        
    def get_stats(self) -> Dict[str, Any]:
        """获取文件系统统计信息"""
        total_files = 0
        total_dirs = 0
        total_size = 0
        
        for root, dirs, files in os.walk(self.config.root_path):
            total_dirs += len(dirs)
            total_files += len(files)
            for f in files:
                try:
                    total_size += os.path.getsize(os.path.join(root, f))
                except:
                    continue
                    
        return {
            'root_path': self.config.root_path,
            'total_files': total_files,
            'total_dirs': total_dirs,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'auth_enabled': self.config.enable_auth,
            'max_file_size_mb': self.config.max_file_size_bytes // (1024 * 1024)
        }
