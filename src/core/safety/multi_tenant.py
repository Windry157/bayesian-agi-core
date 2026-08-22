#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多租户支持模块
提供租户隔离、资源配额和租户管理
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TenantStatus(Enum):
    """租户状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class QuotaType(Enum):
    """配额类型"""
    API_CALLS = "api_calls"
    STORAGE = "storage"
    MEMORY = "memory"
    USERS = "users"
    CONCURRENT_REQUESTS = "concurrent_requests"


@dataclass
class TenantQuota:
    """租户配额"""
    tenant_id: str
    quotas: Dict[QuotaType, int] = field(default_factory=dict)
    usage: Dict[QuotaType, int] = field(default_factory=dict)
    last_reset: float = field(default_factory=time.time)
    
    def get_usage(self, quota_type: QuotaType) -> int:
        """获取配额使用量"""
        return self.usage.get(quota_type, 0)
    
    def get_limit(self, quota_type: QuotaType) -> int:
        """获取配额限制"""
        return self.quotas.get(quota_type, 0)
    
    def increment_usage(self, quota_type: QuotaType, amount: int = 1) -> bool:
        """
        增加配额使用量
        
        Args:
            quota_type: 配额类型
            amount: 增加量
            
        Returns:
            是否在配额范围内
        """
        limit = self.get_limit(quota_type)
        current = self.get_usage(quota_type)
        
        if limit > 0 and current + amount > limit:
            return False
        
        self.usage[quota_type] = current + amount
        return True
    
    def reset_usage(self):
        """重置配额使用量"""
        self.usage.clear()
        self.last_reset = time.time()


@dataclass
class Tenant:
    """租户"""
    tenant_id: str
    name: str
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_ids: Set[str] = field(default_factory=set)
    quota: Optional[TenantQuota] = None


class TenantManager:
    """
    租户管理器
    
    功能:
    - 租户创建和管理
    - 租户配额管理
    - 租户资源隔离
    - 租户状态管理
    """
    
    def __init__(
        self,
        default_quota: Optional[Dict[QuotaType, int]] = None
    ):
        """
        初始化租户管理器
        
        Args:
            default_quota: 默认租户配额
        """
        self._tenants: Dict[str, Tenant] = {}
        self._tenant_quotas: Dict[str, TenantQuota] = {}
        self._lock = asyncio.Lock()
        
        # 默认配额
        self._default_quota = default_quota or {
            QuotaType.API_CALLS: 10000,
            QuotaType.STORAGE: 1024 * 1024 * 100,  # 100MB
            QuotaType.USERS: 10,
            QuotaType.CONCURRENT_REQUESTS: 100
        }
    
    async def create_tenant(
        self,
        tenant_id: str,
        name: str,
        status: TenantStatus = TenantStatus.ACTIVE,
        quota: Optional[Dict[QuotaType, int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tenant:
        """
        创建租户
        
        Args:
            tenant_id: 租户ID
            name: 租户名称
            status: 租户状态
            quota: 自定义配额
            metadata: 附加元数据
            
        Returns:
            创建的租户对象
        """
        async with self._lock:
            if tenant_id in self._tenants:
                raise ValueError(f"租户已存在: {tenant_id}")
            
            # 创建租户配额
            tenant_quota = TenantQuota(
                tenant_id=tenant_id,
                quotas=dict(quota or self._default_quota)
            )
            
            # 创建租户
            tenant = Tenant(
                tenant_id=tenant_id,
                name=name,
                status=status,
                metadata=metadata or {},
                quota=tenant_quota
            )
            
            self._tenants[tenant_id] = tenant
            self._tenant_quotas[tenant_id] = tenant_quota
            
            logger.info(f"🏢 创建租户: {name} ({tenant_id})")
            return tenant
    
    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        return self._tenants.get(tenant_id)
    
    async def update_tenant(
        self,
        tenant_id: str,
        name: Optional[str] = None,
        status: Optional[TenantStatus] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Tenant]:
        """
        更新租户信息
        
        Args:
            tenant_id: 租户ID
            name: 新名称
            status: 新状态
            metadata: 新元数据
            
        Returns:
            更新后的租户对象
        """
        async with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return None
            
            if name is not None:
                tenant.name = name
            if status is not None:
                tenant.status = status
            if metadata is not None:
                tenant.metadata.update(metadata)
            
            logger.info(f"✏️ 更新租户: {tenant_id}")
            return tenant
    
    async def delete_tenant(self, tenant_id: str) -> bool:
        """
        删除租户
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            是否成功删除
        """
        async with self._lock:
            if tenant_id in self._tenants:
                del self._tenants[tenant_id]
                if tenant_id in self._tenant_quotas:
                    del self._tenant_quotas[tenant_id]
                logger.info(f"🗑️ 删除租户: {tenant_id}")
                return True
            return False
    
    async def set_tenant_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        limit: int
    ) -> bool:
        """
        设置租户配额
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            limit: 配额限制
            
        Returns:
            是否成功
        """
        async with self._lock:
            quota = self._tenant_quotas.get(tenant_id)
            if not quota:
                return False
            
            quota.quotas[quota_type] = limit
            logger.info(f"⚙️ 设置租户 {tenant_id} 配额 {quota_type} = {limit}")
            return True
    
    async def check_and_increment_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> bool:
        """
        检查并增加配额使用量
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 增加量
            
        Returns:
            是否在配额范围内
        """
        async with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant or tenant.status != TenantStatus.ACTIVE:
                return False
            
            quota = self._tenant_quotas.get(tenant_id)
            if not quota:
                return False
            
            return quota.increment_usage(quota_type, amount)
    
    async def get_tenant_usage(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        获取租户配额使用情况
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            配额使用情况字典
        """
        async with self._lock:
            quota = self._tenant_quotas.get(tenant_id)
            if not quota:
                return None
            
            usage_info = {}
            for quota_type in QuotaType:
                usage = quota.get_usage(quota_type)
                limit = quota.get_limit(quota_type)
                percentage = (usage / limit * 100) if limit > 0 else 0
                
                usage_info[quota_type.value] = {
                    'usage': usage,
                    'limit': limit,
                    'percentage': round(percentage, 2)
                }
            
            return usage_info
    
    async def reset_tenant_quota(self, tenant_id: str) -> bool:
        """
        重置租户配额使用量
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            quota = self._tenant_quotas.get(tenant_id)
            if not quota:
                return False
            
            quota.reset_usage()
            logger.info(f"🔄 重置租户 {tenant_id} 配额")
            return True
    
    async def add_user_to_tenant(self, tenant_id: str, user_id: str) -> bool:
        """
        将用户添加到租户
        
        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            
            # 检查用户配额
            quota = self._tenant_quotas.get(tenant_id)
            if quota:
                user_limit = quota.get_limit(QuotaType.USERS)
                if user_limit > 0 and len(tenant.user_ids) >= user_limit:
                    return False
            
            tenant.user_ids.add(user_id)
            logger.info(f"👤 添加用户 {user_id} 到租户 {tenant_id}")
            return True
    
    async def remove_user_from_tenant(self, tenant_id: str, user_id: str) -> bool:
        """
        从租户移除用户
        
        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            
            if user_id in tenant.user_ids:
                tenant.user_ids.remove(user_id)
                logger.info(f"👤 从租户 {tenant_id} 移除用户 {user_id}")
                return True
            return False
    
    async def check_tenant_status(self, tenant_id: str) -> Optional[TenantStatus]:
        """
        检查租户状态
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            租户状态，如果租户不存在返回None
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None
        return tenant.status
    
    async def is_tenant_active(self, tenant_id: str) -> bool:
        """
        检查租户是否活跃
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            是否活跃
        """
        status = await self.check_tenant_status(tenant_id)
        return status == TenantStatus.ACTIVE
    
    async def get_all_tenants(self) -> List[Tenant]:
        """获取所有租户"""
        return list(self._tenants.values())
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取租户系统统计"""
        stats = {
            'total_tenants': len(self._tenants),
            'tenants_by_status': {},
            'total_users': 0
        }
        
        for status in TenantStatus:
            stats['tenants_by_status'][status.value] = sum(
                1 for t in self._tenants.values() if t.status == status
            )
        
        for tenant in self._tenants.values():
            stats['total_users'] += len(tenant.user_ids)
        
        return stats


# 全局租户管理器实例
_tenant_manager: Optional[TenantManager] = None


def get_tenant_manager(
    default_quota: Optional[Dict[QuotaType, int]] = None
) -> TenantManager:
    """获取或创建全局租户管理器"""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager(default_quota=default_quota)
    return _tenant_manager
