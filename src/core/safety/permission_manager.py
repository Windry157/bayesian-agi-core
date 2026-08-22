#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权限控制系统
基于角色的访问控制(RBAC)
"""
import asyncio
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举"""
    # 用户管理
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_MANAGE = "user:manage"
    
    # 资源管理
    RESOURCE_READ = "resource:read"
    RESOURCE_WRITE = "resource:write"
    RESOURCE_DELETE = "resource:delete"
    RESOURCE_MANAGE = "resource:manage"
    
    # 记忆系统
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    MEMORY_MANAGE = "memory:manage"
    
    # 推理系统
    REASONING_USE = "reasoning:use"
    REASONING_CONFIG = "reasoning:config"
    
    # 系统管理
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_ADMIN = "system:admin"
    
    # 审计日志
    AUDIT_READ = "audit:read"
    AUDIT_MANAGE = "audit:manage"
    
    # API访问
    API_ACCESS = "api:access"
    API_ADMIN = "api:admin"


class Role(Enum):
    """角色枚举"""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"
    SYSTEM = "system"


# 角色权限映射
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.USER_MANAGE,
        Permission.RESOURCE_MANAGE,
        Permission.MEMORY_MANAGE,
        Permission.REASONING_CONFIG,
        Permission.SYSTEM_ADMIN,
        Permission.AUDIT_MANAGE,
        Permission.API_ADMIN,
    },
    Role.MANAGER: {
        Permission.USER_READ,
        Permission.RESOURCE_MANAGE,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.REASONING_USE,
        Permission.SYSTEM_MONITOR,
        Permission.AUDIT_READ,
        Permission.API_ACCESS,
    },
    Role.USER: {
        Permission.RESOURCE_READ,
        Permission.RESOURCE_WRITE,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.REASONING_USE,
        Permission.API_ACCESS,
    },
    Role.GUEST: {
        Permission.RESOURCE_READ,
        Permission.MEMORY_READ,
        Permission.REASONING_USE,
    },
    Role.SYSTEM: {perm for perm in Permission},  # 系统角色拥有所有权限
}


@dataclass
class User:
    """用户"""
    user_id: str
    username: str
    tenant_id: Optional[str] = None
    roles: Set[Role] = field(default_factory=set)
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_role(self, role: Role) -> bool:
        """检查用户是否拥有指定角色"""
        return role in self.roles
    
    def get_all_permissions(self) -> Set[Permission]:
        """获取用户的所有权限(包括角色权限和直接权限)"""
        all_perms = set(self.permissions)
        for role in self.roles:
            all_perms.update(ROLE_PERMISSIONS.get(role, set()))
        return all_perms


@dataclass
class Resource:
    """受保护资源"""
    resource_id: str
    resource_type: str
    owner_id: str
    tenant_id: Optional[str] = None
    required_permissions: Set[Permission] = field(default_factory=set)
    is_public: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class PermissionManager:
    """
    权限管理器
    
    功能:
    - 基于角色的访问控制(RBAC)
    - 资源级权限控制
    - 多租户支持
    - 权限检查
    """
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._resources: Dict[str, Resource] = {}
        self._user_roles: Dict[str, Set[Role]] = {}
        self._role_permissions: Dict[Role, Set[Permission]] = dict(ROLE_PERMISSIONS)
        self._lock = asyncio.Lock()
    
    async def create_user(
        self,
        user_id: str,
        username: str,
        roles: Optional[List[Union[Role, str]]] = None,
        tenant_id: Optional[str] = None,
        permissions: Optional[List[Union[Permission, str]]] = None
    ) -> User:
        """
        创建用户
        
        Args:
            user_id: 用户ID
            username: 用户名
            roles: 角色列表
            tenant_id: 租户ID
            permissions: 直接权限列表
            
        Returns:
            创建的用户对象
        """
        async with self._lock:
            role_set = set()
            if roles:
                for role in roles:
                    if isinstance(role, str):
                        role = Role(role)
                    role_set.add(role)
            
            perm_set = set()
            if permissions:
                for perm in permissions:
                    if isinstance(perm, str):
                        perm = Permission(perm)
                    perm_set.add(perm)
            
            user = User(
                user_id=user_id,
                username=username,
                tenant_id=tenant_id,
                roles=role_set,
                permissions=perm_set
            )
            
            self._users[user_id] = user
            logger.info(f"👤 创建用户: {username} ({user_id})")
            return user
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self._users.get(user_id)
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        async with self._lock:
            if user_id in self._users:
                del self._users[user_id]
                logger.info(f"🗑️ 删除用户: {user_id}")
                return True
            return False
    
    async def assign_role(self, user_id: str, role: Union[Role, str]) -> bool:
        """
        给用户分配角色
        
        Args:
            user_id: 用户ID
            role: 角色
            
        Returns:
            是否成功
        """
        async with self._lock:
            user = self._users.get(user_id)
            if not user:
                logger.warning(f"⚠️ 用户不存在: {user_id}")
                return False
            
            if isinstance(role, str):
                role = Role(role)
            
            user.roles.add(role)
            logger.info(f"✅ 用户 {user_id} 获得角色: {role}")
            return True
    
    async def revoke_role(self, user_id: str, role: Union[Role, str]) -> bool:
        """
        撤销用户角色
        
        Args:
            user_id: 用户ID
            role: 角色
            
        Returns:
            是否成功
        """
        async with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False
            
            if isinstance(role, str):
                role = Role(role)
            
            if role in user.roles:
                user.roles.remove(role)
                logger.info(f"✅ 用户 {user_id} 失去角色: {role}")
                return True
            return False
    
    async def assign_permission(
        self,
        user_id: str,
        permission: Union[Permission, str]
    ) -> bool:
        """
        给用户直接分配权限
        
        Args:
            user_id: 用户ID
            permission: 权限
            
        Returns:
            是否成功
        """
        async with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False
            
            if isinstance(permission, str):
                permission = Permission(permission)
            
            user.permissions.add(permission)
            logger.info(f"✅ 用户 {user_id} 获得权限: {permission}")
            return True
    
    async def revoke_permission(
        self,
        user_id: str,
        permission: Union[Permission, str]
    ) -> bool:
        """
        撤销用户直接权限
        
        Args:
            user_id: 用户ID
            permission: 权限
            
        Returns:
            是否成功
        """
        async with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False
            
            if isinstance(permission, str):
                permission = Permission(permission)
            
            if permission in user.permissions:
                user.permissions.remove(permission)
                logger.info(f"✅ 用户 {user_id} 失去权限: {permission}")
                return True
            return False
    
    async def check_permission(
        self,
        user_id: str,
        permission: Union[Permission, str],
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        检查用户是否拥有指定权限
        
        Args:
            user_id: 用户ID
            permission: 权限
            tenant_id: 租户ID(用于多租户检查)
            
        Returns:
            是否拥有权限
        """
        user = self._users.get(user_id)
        if not user or not user.is_active:
            return False
        
        # 检查租户
        if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
            return False
        
        if isinstance(permission, str):
            permission = Permission(permission)
        
        user_perms = user.get_all_permissions()
        return permission in user_perms
    
    async def check_any_permission(
        self,
        user_id: str,
        permissions: List[Union[Permission, str]],
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        检查用户是否拥有任一指定权限
        
        Args:
            user_id: 用户ID
            permissions: 权限列表
            tenant_id: 租户ID
            
        Returns:
            是否拥有任一权限
        """
        for perm in permissions:
            if await self.check_permission(user_id, perm, tenant_id):
                return True
        return False
    
    async def check_all_permissions(
        self,
        user_id: str,
        permissions: List[Union[Permission, str]],
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        检查用户是否拥有所有指定权限
        
        Args:
            user_id: 用户ID
            permissions: 权限列表
            tenant_id: 租户ID
            
        Returns:
            是否拥有所有权限
        """
        for perm in permissions:
            if not await self.check_permission(user_id, perm, tenant_id):
                return False
        return True
    
    async def register_resource(
        self,
        resource_id: str,
        resource_type: str,
        owner_id: str,
        tenant_id: Optional[str] = None,
        required_permissions: Optional[List[Union[Permission, str]]] = None,
        is_public: bool = False
    ) -> Resource:
        """
        注册受保护资源
        
        Args:
            resource_id: 资源ID
            resource_type: 资源类型
            owner_id: 所有者ID
            tenant_id: 租户ID
            required_permissions: 访问所需权限
            is_public: 是否公开
            
        Returns:
            资源对象
        """
        async with self._lock:
            perm_set = set()
            if required_permissions:
                for perm in required_permissions:
                    if isinstance(perm, str):
                        perm = Permission(perm)
                    perm_set.add(perm)
            
            resource = Resource(
                resource_id=resource_id,
                resource_type=resource_type,
                owner_id=owner_id,
                tenant_id=tenant_id,
                required_permissions=perm_set,
                is_public=is_public
            )
            
            self._resources[resource_id] = resource
            logger.info(f"📦 注册资源: {resource_type}/{resource_id}")
            return resource
    
    async def check_resource_access(
        self,
        user_id: str,
        resource_id: str,
        permission: Optional[Union[Permission, str]] = None
    ) -> bool:
        """
        检查用户是否可以访问资源
        
        Args:
            user_id: 用户ID
            resource_id: 资源ID
            permission: 额外需要的权限
            
        Returns:
            是否可以访问
        """
        resource = self._resources.get(resource_id)
        if not resource:
            return False
        
        # 公开资源
        if resource.is_public:
            return True
        
        user = self._users.get(user_id)
        if not user or not user.is_active:
            return False
        
        # 资源所有者
        if resource.owner_id == user_id:
            return True
        
        # 租户检查
        if resource.tenant_id and user.tenant_id and resource.tenant_id != user.tenant_id:
            return False
        
        # 检查所需权限
        if resource.required_permissions:
            user_perms = user.get_all_permissions()
            if not resource.required_permissions.intersection(user_perms):
                return False
        
        # 检查额外权限
        if permission:
            if not await self.check_permission(user_id, permission, resource.tenant_id):
                return False
        
        return True
    
    def get_role_permissions(self, role: Union[Role, str]) -> Set[Permission]:
        """获取角色的所有权限"""
        if isinstance(role, str):
            role = Role(role)
        return self._role_permissions.get(role, set())
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取权限系统统计"""
        return {
            'total_users': len(self._users),
            'total_resources': len(self._resources),
            'active_users': sum(1 for u in self._users.values() if u.is_active),
            'users_by_role': {
                role.value: sum(1 for u in self._users.values() if role in u.roles)
                for role in Role
            }
        }


# 全局权限管理器实例
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """获取或创建全局权限管理器"""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


def require_permission(
    permission: Union[Permission, str],
    tenant_check: bool = True
):
    """
    权限检查装饰器
    
    Args:
        permission: 需要的权限
        tenant_check: 是否检查租户
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            perm_manager = get_permission_manager()
            user_id = kwargs.get('user_id')
            
            if not user_id:
                raise PermissionError("未提供用户ID")
            
            tenant_id = kwargs.get('tenant_id') if tenant_check else None
            
            if not await perm_manager.check_permission(user_id, permission, tenant_id):
                raise PermissionError(f"权限不足: {permission}")
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            perm_manager = get_permission_manager()
            user_id = kwargs.get('user_id')
            
            if not user_id:
                raise PermissionError("未提供用户ID")
            
            tenant_id = kwargs.get('tenant_id') if tenant_check else None
            
            loop = asyncio.get_event_loop()
            has_perm = loop.run_until_complete(
                perm_manager.check_permission(user_id, permission, tenant_id)
            )
            
            if not has_perm:
                raise PermissionError(f"权限不足: {permission}")
            
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
