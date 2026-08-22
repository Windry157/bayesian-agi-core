"""
认证管理器 - 提供用户认证和权限控制
"""
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from .models import UserCredentials, AccessToken, PermissionLevel
import logging

logger = logging.getLogger(__name__)

@dataclass
class AuthConfig:
    """认证配置"""
    token_expiry_minutes: int = 60
    max_tokens_per_user: int = 5
    allow_anonymous_read: bool = False

class AuthManager:
    """认证管理器"""
    
    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig()
        self._users: Dict[str, UserCredentials] = {}
        self._tokens: Dict[str, AccessToken] = {}
        self._load_default_users()
        
    def _load_default_users(self):
        """加载默认用户"""
        self._users['admin'] = UserCredentials(
            username='admin',
            password_hash=self._hash_password('admin123'),
            permissions=PermissionLevel.ADMIN,
            allowed_paths=['/']
        )
        self._users['user'] = UserCredentials(
            username='user',
            password_hash=self._hash_password('user123'),
            permissions=PermissionLevel.READ,
            allowed_paths=['/documents', '/data']
        )
        logger.info(f"✅ 已加载 {len(self._users)} 个默认用户")
        
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
        
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """用户认证，返回访问令牌"""
        user = self._users.get(username)
        if not user:
            logger.warning(f"❌ 用户不存在: {username}")
            return None
            
        if user.password_hash != self._hash_password(password):
            logger.warning(f"❌ 密码错误: {username}")
            return None
            
        return self._generate_token(username, user.permissions)
        
    def _generate_token(self, username: str, permissions: PermissionLevel) -> str:
        """生成访问令牌"""
        user_tokens = [t for t in self._tokens.values() if t.username == username]
        if len(user_tokens) >= self.config.max_tokens_per_user:
            oldest_token = min(user_tokens, key=lambda t: t.expires_at)
            del self._tokens[oldest_token.token]
            
        token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(minutes=self.config.token_expiry_minutes)
        
        self._tokens[token] = AccessToken(
            token=token,
            username=username,
            expires_at=expires_at,
            permissions=permissions
        )
        
        logger.info(f"✅ 生成新令牌: {username}")
        return token
        
    def validate_token(self, token: str) -> Optional[AccessToken]:
        """验证令牌"""
        access_token = self._tokens.get(token)
        if not access_token:
            return None
            
        if not access_token.is_valid():
            del self._tokens[token]
            return None
            
        return access_token
        
    def revoke_token(self, token: str) -> bool:
        """撤销令牌"""
        if token in self._tokens:
            del self._tokens[token]
            logger.info(f"✅ 令牌已撤销")
            return True
        return False
        
    def check_permission(self, token: str, path: str, required_permission: PermissionLevel) -> bool:
        """检查权限"""
        if self.config.allow_anonymous_read and required_permission == PermissionLevel.READ:
            return True
            
        access_token = self.validate_token(token)
        if not access_token:
            return False
            
        user = self._users.get(access_token.username)
        if not user:
            return False
            
        if access_token.permissions == PermissionLevel.ADMIN:
            return True
            
        if access_token.permissions.value not in ['read', 'write']:
            return False
            
        if required_permission == PermissionLevel.WRITE and access_token.permissions != PermissionLevel.WRITE:
            return False
            
        if not user.allowed_paths:
            return True
            
        for allowed_path in user.allowed_paths:
            if path.startswith(allowed_path):
                return True
                
        return False
        
    def add_user(self, username: str, password: str, permissions: PermissionLevel, allowed_paths: List[str] = None):
        """添加用户"""
        if username in self._users:
            raise ValueError(f"用户已存在: {username}")
            
        self._users[username] = UserCredentials(
            username=username,
            password_hash=self._hash_password(password),
            permissions=permissions,
            allowed_paths=allowed_paths or []
        )
        logger.info(f"✅ 添加用户: {username}")
        
    def remove_user(self, username: str):
        """删除用户"""
        if username not in self._users:
            raise ValueError(f"用户不存在: {username}")
            
        del self._users[username]
        for token in list(self._tokens.keys()):
            if self._tokens[token].username == username:
                del self._tokens[token]
        logger.info(f"✅ 删除用户: {username}")
        
    def get_user_info(self, username: str) -> Optional[UserCredentials]:
        """获取用户信息"""
        return self._users.get(username)
        
    def get_active_tokens(self) -> List[AccessToken]:
        """获取活跃令牌"""
        valid_tokens = []
        for token in list(self._tokens.keys()):
            if self._tokens[token].is_valid():
                valid_tokens.append(self._tokens[token])
            else:
                del self._tokens[token]
        return valid_tokens
