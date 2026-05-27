#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能优化和企业功能综合测试
"""
import pytest
import asyncio
import time
from src.core.cache.lru_cache import LRUCache, get_lru_cache, lru_cache_decorator
from src.core.cognition.reasoning_optimizer import (
    ReasoningOptimizer,
    get_reasoning_optimizer,
    optimize_reasoning
)
from src.core.monitoring.audit_logger import (
    AuditLogger,
    get_audit_logger,
    AuditEventType,
    AuditLevel
)
from src.core.safety.permission_manager import (
    PermissionManager,
    get_permission_manager,
    Role,
    Permission
)
from src.core.safety.multi_tenant import (
    TenantManager,
    get_tenant_manager,
    TenantStatus,
    QuotaType
)


class TestLRUCache:
    """LRU缓存测试"""
    
    @pytest.mark.asyncio
    async def test_lru_cache_basic(self):
        """测试基本缓存功能"""
        cache = LRUCache(max_size=100, default_ttl=3600)
        
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_lru_cache_eviction(self):
        """测试LRU淘汰机制"""
        cache = LRUCache(max_size=5, default_ttl=3600)
        
        for i in range(10):
            await cache.set(f"key{i}", f"value{i}")
        
        stats = await cache.get_stats()
        assert stats['size'] <= 5  # 应该淘汰了旧条目
    
    @pytest.mark.asyncio
    async def test_lru_cache_ttl(self):
        """测试TTL过期"""
        cache = LRUCache(max_size=100, default_ttl=1)
        
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"
        
        await asyncio.sleep(1.1)
        assert await cache.get("key1") is None
    
    @pytest.mark.asyncio
    async def test_lru_cache_stats(self):
        """测试统计功能"""
        cache = LRUCache(max_size=100, default_ttl=3600)
        
        await cache.set("key1", "value1")
        await cache.get("key1")
        await cache.get("key1")
        await cache.get("nonexistent")
        
        stats = await cache.get_stats()
        
        assert stats['hits'] == 2
        assert stats['misses'] == 1


class TestReasoningOptimizer:
    """推理优化器测试"""
    
    @pytest.mark.asyncio
    async def test_cached_reasoning(self):
        """测试推理缓存"""
        optimizer = ReasoningOptimizer(cache_ttl=300, max_cache_size=100)
        
        call_count = 0
        
        async def slow_function(x):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * 2
        
        # 第一次调用
        result1 = await optimizer.cached_reasoning(
            slow_function,
            "test_reasoning",
            5
        )
        
        # 第二次调用应该用缓存
        result2 = await optimizer.cached_reasoning(
            slow_function,
            "test_reasoning",
            5
        )
        
        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # 只执行了一次
    
    @pytest.mark.asyncio
    async def test_reasoning_stats(self):
        """测试统计功能"""
        optimizer = ReasoningOptimizer()
        
        async def func(x):
            return x
        
        await optimizer.cached_reasoning(func, "test", 1)
        await optimizer.cached_reasoning(func, "test", 2)
        
        stats = optimizer.get_stats()
        
        assert stats['total_inferences'] >= 1


class TestAuditLogger:
    """审计日志测试"""
    
    @pytest.mark.asyncio
    async def test_audit_log_basic(self):
        """测试基本日志功能"""
        logger = AuditLogger(log_file=None, max_events_in_memory=100)
        
        event_id = await logger.log_event(
            event_type=AuditEventType.USER_LOGIN,
            event_level=AuditLevel.INFO,
            user_id="user1",
            user_name="testuser"
        )
        
        assert event_id is not None
    
    @pytest.mark.asyncio
    async def test_audit_query(self):
        """测试查询功能"""
        logger = AuditLogger(log_file=None, max_events_in_memory=100)
        
        await logger.log_event(
            event_type=AuditEventType.API_CALL,
            user_id="user1"
        )
        
        events = logger.query_events(user_id="user1")
        assert len(events) > 0
    
    @pytest.mark.asyncio
    async def test_audit_stats(self):
        """测试统计功能"""
        logger = AuditLogger(log_file=None, max_events_in_memory=100)
        
        await logger.log_event(AuditEventType.USER_LOGIN, user_id="user1")
        await logger.log_event(AuditEventType.API_CALL, user_id="user1")
        
        stats = logger.get_stats()
        assert stats['total_events'] >= 2


class TestPermissionManager:
    """权限管理测试"""
    
    @pytest.mark.asyncio
    async def test_create_user(self):
        """测试创建用户"""
        manager = PermissionManager()
        
        user = await manager.create_user(
            user_id="user1",
            username="testuser",
            roles=[Role.USER]
        )
        
        assert user.user_id == "user1"
        assert Role.USER in user.roles
    
    @pytest.mark.asyncio
    async def test_permission_check(self):
        """测试权限检查"""
        manager = PermissionManager()
        
        await manager.create_user(
            user_id="admin1",
            username="admin",
            roles=[Role.ADMIN]
        )
        
        has_perm = await manager.check_permission(
            "admin1",
            Permission.SYSTEM_ADMIN
        )
        
        assert has_perm == True
    
    @pytest.mark.asyncio
    async def test_resource_access(self):
        """测试资源访问控制"""
        manager = PermissionManager()
        
        await manager.create_user("user1", "user1", roles=[Role.USER])
        await manager.register_resource(
            resource_id="res1",
            resource_type="memory",
            owner_id="user1",
            required_permissions=[Permission.MEMORY_READ]
        )
        
        can_access = await manager.check_resource_access("user1", "res1")
        assert can_access == True


class TestTenantManager:
    """租户管理测试"""
    
    @pytest.mark.asyncio
    async def test_create_tenant(self):
        """测试创建租户"""
        manager = TenantManager()
        
        tenant = await manager.create_tenant(
            tenant_id="tenant1",
            name="Test Tenant",
            status=TenantStatus.ACTIVE
        )
        
        assert tenant.tenant_id == "tenant1"
    
    @pytest.mark.asyncio
    async def test_tenant_quota(self):
        """测试配额管理"""
        manager = TenantManager()
        
        await manager.create_tenant("tenant1", "Test Tenant")
        
        await manager.set_tenant_quota("tenant1", QuotaType.API_CALLS, 100)
        
        for i in range(50):
            success = await manager.check_and_increment_quota(
                "tenant1",
                QuotaType.API_CALLS
            )
            assert success == True
        
        usage = await manager.get_tenant_usage("tenant1")
        assert usage is not None
    
    @pytest.mark.asyncio
    async def test_tenant_user(self):
        """测试租户用户管理"""
        manager = TenantManager()
        
        await manager.create_tenant("tenant1", "Test Tenant")
        
        success = await manager.add_user_to_tenant("tenant1", "user1")
        assert success == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
