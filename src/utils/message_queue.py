#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息队列模块
处理服务间的通信
"""

import pika
import json
import logging
from typing import Callable, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MessageQueueManager:
    """消息队列管理器

    处理服务间的通信

    NOTE: 此模块需要 RabbitMQ 服务运行。如果 RabbitMQ 不可用，
    publish() 方法将记录警告并返回，subscribe() 方法将抛出异常。
    请确保在生产环境中配置并运行 RabbitMQ。
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        password: str = "guest",
    ):
        """初始化消息队列管理器

        Args:
            host: RabbitMQ主机地址
            port: RabbitMQ端口
            username: RabbitMQ用户名
            password: RabbitMQ密码
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None
        self.callbacks = {}
        self._connected = False

    def connect(self):
        """连接到RabbitMQ

        如果连接失败，会设置 _connected = False 并记录警告。
        后续的 publish/subscribe 调用应该处理这种情况。
        """
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host, port=self.port, credentials=credentials,
                    connection_attempts=3,
                    retry_delay=1
                )
            )
            self.channel = self.connection.channel()
            self._connected = True
            logger.info("成功连接到RabbitMQ")
        except Exception as e:
            self._connected = False
            logger.warning(f"RabbitMQ未连接: {e}。消息队列功能将被禁用。")
            # 不再抛出异常，允许服务在没有RabbitMQ的情况下运行

    def disconnect(self):
        """断开与RabbitMQ的连接"""
        if self.connection:
            try:
                self.connection.close()
                self._connected = False
                logger.info("成功断开与RabbitMQ的连接")
            except Exception as e:
                logger.error(f"断开RabbitMQ连接失败: {e}")

    def is_connected(self) -> bool:
        """检查是否已连接到RabbitMQ

        Returns:
            是否已连接
        """
        return self._connected and self.connection is not None and self.connection.is_open

    def declare_queue(self, queue_name: str):
        """声明队列

        Args:
            queue_name: 队列名称
        """
        if not self.channel:
            self.connect()

        try:
            self.channel.queue_declare(queue=queue_name, durable=True)
            logger.info(f"成功声明队列: {queue_name}")
        except Exception as e:
            logger.error(f"声明队列失败: {e}")
            raise

    def publish(self, queue_name: str, message: Dict[str, Any]):
        """发布消息

        Args:
            queue_name: 队列名称
            message: 消息内容

        Note:
            如果RabbitMQ未连接，会记录警告并静默返回。
            调用方应该使用HTTP或其他方式作为备用方案。
        """
        if not self._connected:
            logger.warning(f"RabbitMQ未连接，跳过消息发布到队列 {queue_name}: {message}")
            return

        try:
            if not self.channel:
                self.connect()

            if self._connected:
                self.declare_queue(queue_name)
                self.channel.basic_publish(
                    exchange="",
                    routing_key=queue_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # 消息持久化
                    ),
                )
                logger.info(f"成功发布消息到队列 {queue_name}")
        except Exception as e:
            logger.error(f"发布消息失败: {e}")
            # 不抛出异常，允许服务继续运行

    def subscribe(self, queue_name: str, callback: Callable[[Dict[str, Any]], None]):
        """订阅消息

        Args:
            queue_name: 队列名称
            callback: 回调函数，用于处理接收到的消息
        """
        if not self.channel:
            self.connect()

        try:
            self.declare_queue(queue_name)

            def on_message(ch, method, properties, body):
                try:
                    message = json.loads(body)
                    callback(message)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"处理消息失败: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag)

            self.channel.basic_consume(
                queue=queue_name, on_message_callback=on_message, auto_ack=False
            )

            self.callbacks[queue_name] = callback
            logger.info(f"成功订阅队列: {queue_name}")
        except Exception as e:
            logger.error(f"订阅队列失败: {e}")
            raise

    def start_consuming(self):
        """开始消费消息"""
        if not self.channel:
            self.connect()

        try:
            logger.info("开始消费消息")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("停止消费消息")
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"消费消息失败: {e}")
            raise

    def stop_consuming(self):
        """停止消费消息"""
        if self.channel:
            try:
                self.channel.stop_consuming()
                logger.info("成功停止消费消息")
            except Exception as e:
                logger.error(f"停止消费消息失败: {e}")


# 全局消息队列管理器实例
message_queue_manager = MessageQueueManager()
