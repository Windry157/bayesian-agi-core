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

    def connect(self):
        """连接到RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host, port=self.port, credentials=credentials
                )
            )
            self.channel = self.connection.channel()
            logger.info("成功连接到RabbitMQ")
        except Exception as e:
            logger.error(f"连接RabbitMQ失败: {e}")
            raise

    def disconnect(self):
        """断开与RabbitMQ的连接"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("成功断开与RabbitMQ的连接")
            except Exception as e:
                logger.error(f"断开RabbitMQ连接失败: {e}")

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
        """
        if not self.channel:
            self.connect()

        try:
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
            raise

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
