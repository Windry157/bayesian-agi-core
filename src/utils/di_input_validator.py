#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DI 容器输入校验模块 - 阶段 2.1

确保所有入口点都经过严格的类型、范围和格式校验。

校验规则:
1. interface_type 必须是类型（不能是 None、字符串、实例）
2. implementation_type 必须是类型且可实例化
3. scope 必须是有效的 Scope 枚举值
4. factory 必须是可调用对象（如果提供）
"""

from typing import Any, Callable, Type, TypeVar, Optional
from inspect import isclass, isfunction, ismethod
from .di_exceptions import InvalidRegistrationException
from .di_types import Scope

T = TypeVar("T")


class InputValidator:
    """输入校验器

    对所有 DI 容器的入口点进行严格校验，
    确保坏数据不会进入系统。
    """

    @staticmethod
    def validate_interface_type(interface_type: Any) -> Type:
        """校验接口类型

        Args:
            interface_type: 待校验的接口类型

        Returns:
            校验后的类型

        Raises:
            InvalidRegistrationException: 如果校验失败
        """
        if interface_type is None:
            raise InvalidRegistrationException(
                "interface_type 不能为 None。"
                "请提供一个有效的类型（如 Protocol 或普通类）。"
            )

        if isinstance(interface_type, str):
            raise InvalidRegistrationException(
                f"interface_type 不能是字符串 '{interface_type}'。"
                f"请使用类型本身，而不是类型名称。"
            )

        if not isclass(interface_type) and not hasattr(interface_type, "__protocol__"):
            # Protocol 类型可能不是 class，但有 __protocol__ 属性
            if not hasattr(interface_type, "__mro__"):
                raise InvalidRegistrationException(
                    f"'{interface_type}' 不是有效的类型。"
                    f"请使用 Protocol 或普通类作为接口类型。"
                )

        return interface_type

    @staticmethod
    def validate_implementation_type(
        implementation_type: Any, interface_type: Type
    ) -> Type:
        """校验实现类型

        Args:
            implementation_type: 待校验的实现类型
            interface_type: 接口类型（用于兼容性检查）

        Returns:
            校验后的类型

        Raises:
            InvalidRegistrationException: 如果校验失败
        """
        if implementation_type is None:
            raise InvalidRegistrationException(
                "implementation_type 不能为 None。"
                "请提供一个可实例化的类。"
            )

        if isinstance(implementation_type, str):
            raise InvalidRegistrationException(
                f"implementation_type 不能是字符串 '{implementation_type}'。"
                f"请使用类本身，而不是类名称。"
            )

        if not isclass(implementation_type):
            raise InvalidRegistrationException(
                f"'{implementation_type}' 不是类。"
                f"implementation_type 必须是一个可实例化的类。"
            )

        # 检查是否可实例化
        try:
            # 不实际创建实例，只检查构造函数是否存在
            if not hasattr(implementation_type, "__init__"):
                raise InvalidRegistrationException(
                    f"'{implementation_type.__name__}' 没有 __init__ 方法。"
                    f"请确保它是一个可实例化的类。"
                )
        except AttributeError as e:
            raise InvalidRegistrationException(
                f"'{implementation_type}' 无法检查构造函数: {e}"
            )

        return implementation_type

    @staticmethod
    def validate_scope(scope: Any) -> Scope:
        """校验作用域

        Args:
            scope: 待校验的作用域

        Returns:
            校验后的 Scope 枚举值

        Raises:
            InvalidRegistrationException: 如果校验失败
        """
        if scope is None:
            raise InvalidRegistrationException(
                "scope 不能为 None。"
                "请使用 Scope.SINGLETON, Scope.SCOPED 或 Scope.TRANSIENT。"
            )

        if isinstance(scope, str):
            valid_values = ["singleton", "scoped", "transient"]
            if scope.lower() not in valid_values:
                raise InvalidRegistrationException(
                    f"无效的作用域字符串 '{scope}'。"
                    f"有效值: {valid_values}"
                )
            # 转换字符串为枚举
            return Scope(scope.lower())

        if not isinstance(scope, Scope):
            raise InvalidRegistrationException(
                f"'{scope}' 不是有效的 Scope 枚举值。"
                f"请使用 Scope.SINGLETON, Scope.SCOPED 或 Scope.TRANSIENT。"
            )

        return scope

    @staticmethod
    def validate_factory(factory: Any) -> Optional[Callable]:
        """校验工厂函数

        Args:
            factory: 待校验的工厂函数

        Returns:
            校验后的工厂函数（或 None）

        Raises:
            InvalidRegistrationException: 如果校验失败
        """
        if factory is None:
            return None

        if not callable(factory):
            raise InvalidRegistrationException(
                f"'{factory}' 不是可调用对象。"
                f"factory 必须是一个函数或可调用对象。"
            )

        return factory

    @staticmethod
    def validate_instance(instance: Any, scope: Scope) -> Optional[Any]:
        """校验预创建实例

        Args:
            instance: 待校验的实例
            scope: 作用域

        Returns:
            校验后的实例（或 None）

        Raises:
            InvalidRegistrationException: 如果校验失败
        """
        if instance is None:
            return None

        if scope != Scope.SINGLETON:
            raise InvalidRegistrationException(
                f"预创建实例仅支持 SINGLETON 作用域，当前作用域: {scope.value}。"
                f"如果需要其他作用域，请使用 factory 参数。"
            )

        return instance

    @classmethod
    def validate_registration(
        cls,
        interface_type: Any,
        implementation_type: Any,
        scope: Any,
        instance: Any = None,
        factory: Any = None,
    ) -> dict:
        """校验完整的注册参数

        Args:
            interface_type: 接口类型
            implementation_type: 实现类型
            scope: 作用域
            instance: 预创建实例
            factory: 工厂函数

        Returns:
            校验后的参数字典

        Raises:
            InvalidRegistrationException: 如果任何校验失败
        """
        # 逐步校验，提供清晰的错误信息
        validated_interface = cls.validate_interface_type(interface_type)
        validated_implementation = cls.validate_implementation_type(
            implementation_type, validated_interface
        )
        validated_scope = cls.validate_scope(scope)
        validated_factory = cls.validate_factory(factory)
        validated_instance = cls.validate_instance(instance, validated_scope)

        # 互斥校验：instance 和 factory 不能同时提供
        if validated_instance is not None and validated_factory is not None:
            raise InvalidRegistrationException(
                "instance 和 factory 不能同时提供。"
                "请选择其中一种方式创建实例。"
            )

        return {
            "interface_type": validated_interface,
            "implementation_type": validated_implementation,
            "scope": validated_scope,
            "instance": validated_instance,
            "factory": validated_factory,
        }