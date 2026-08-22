#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体关系查询演示脚本
演示如何查询两个实体之间的间接关系
"""

import asyncio
import shutil
import os

from src.core.memory.memory_system import MemorySystem


async def demo_entity_relation_query():
    print("=== 实体关系查询演示 ===")
    print("目标: 查询 '2024年' 和 '1999年' 之间是否存在间接关系\n")
    
    test_dir = "demo_knowledge_graph"
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    
    # 创建记忆系统（启用知识图谱）
    mem = MemorySystem(memory_dir=test_dir, use_knowledge_graph=True, use_vector_index=False)
    await mem.load()
    
    # ========== 步骤1: 添加包含相关实体的记忆 ==========
    print("【步骤1】添加包含时间实体的记忆")
    
    # 记忆1: 张三在2024年加入阿里巴巴
    mem_id1 = await mem.add_memory("张三在2024年加入阿里巴巴，开始从事机器学习研究")
    print(f"  记忆1: {mem_id1}")
    
    # 记忆2: 阿里巴巴成立于1999年
    mem_id2 = await mem.add_memory("阿里巴巴成立于1999年，是一家知名的科技公司")
    print(f"  记忆2: {mem_id2}")
    
    # 记忆3: 张三的职业生涯
    mem_id3 = await mem.add_memory("张三在加入阿里巴巴之前，曾在多家科技公司工作")
    print(f"  记忆3: {mem_id3}")
    
    print(f"\n知识图谱状态: {mem.knowledge_graph.get_entity_count()} 个实体, {mem.knowledge_graph.get_relation_count()} 条关系")
    
    # ========== 步骤2: 查看所有实体 ==========
    print("\n【步骤2】查看知识图谱中的实体")
    entities = []
    
    if isinstance(mem.knowledge_graph.graph, dict) and "nodes" in mem.knowledge_graph.graph:
        for node_id, data in mem.knowledge_graph.graph["nodes"].items():
            entities.append({"id": node_id, "name": data.get("name"), "type": data.get("type")})
            print(f"  - {node_id[:10]}... [{data.get('type')}]: '{data.get('name')}'")
    
    # ========== 步骤3: 查询实体关系 ==========
    print("\n【步骤3】查询 '2024年' 相关的关系")
    relations_2024 = await mem.get_entity_relations("2024年")
    print(f"  '2024年' 的直接关系: {len(relations_2024)} 条")
    for rel in relations_2024:
        print(f"    {rel['source'][:10]}... -[{rel['relation']}]-> {rel['target'][:10]}...")
    
    print("\n【步骤4】查询 '1999年' 相关的关系")
    relations_1999 = await mem.get_entity_relations("1999年")
    print(f"  '1999年' 的直接关系: {len(relations_1999)} 条")
    for rel in relations_2024:
        print(f"    {rel['source'][:10]}... -[{rel['relation']}]-> {rel['target'][:10]}...")
    
    # ========== 步骤4: 查找两个实体之间的路径 ==========
    print("\n【步骤5】查找 '2024年' 和 '1999年' 之间的路径")
    
    # 找到包含"2024年"和"1999年"的实体ID
    entity_2024_id = None
    entity_1999_id = None
    
    if isinstance(mem.knowledge_graph.graph, dict) and "nodes" in mem.knowledge_graph.graph:
        for node_id, data in mem.knowledge_graph.graph["nodes"].items():
            if data.get("name") == "2024年":
                entity_2024_id = node_id
            if data.get("name") == "1999年":
                entity_1999_id = node_id
    
    if entity_2024_id and entity_1999_id:
        print(f"  找到实体:")
        print(f"    2024年: {entity_2024_id}")
        print(f"    1999年: {entity_1999_id}")
        
        # 查找路径
        paths = mem.knowledge_graph.query_path(entity_2024_id, entity_1999_id, max_depth=3)
        
        if paths:
            print(f"\n  找到 {len(paths)} 条路径:")
            for i, path in enumerate(paths):
                print(f"    路径 {i+1}: {' -> '.join([p[:10] + '...' for p in path])}")
                
                # 解析路径中的关系
                path_relations = []
                for j in range(len(path) - 1):
                    for edge in mem.knowledge_graph.graph["edges"]:
                        if edge["source"] == path[j] and edge["target"] == path[j+1]:
                            path_relations.append(edge["relation"])
                            break
                
                if path_relations:
                    print(f"        关系链: {' -> '.join(path_relations)}")
        else:
            print("\n  未找到直接路径，尝试知识推理...")
            
            # 使用推理功能
            inferences = await mem.infer_knowledge("2024年和1999年的关系")
            if inferences:
                print(f"  推理结果: {len(inferences)} 条")
                for inf in inferences:
                    print(f"    {inf.get('source', '')} - {inf.get('relation', '')} -> {inf.get('target', '')} (置信度: {inf.get('confidence', 0)})")
            else:
                print("  当前知识图谱中'2024年'和'1999年'之间没有直接或间接关系")
                print("  原因: 两个实体分别来自不同的记忆，尚未建立关联")
                print("\n  解决方案: 添加一条连接两个时间点的记忆")
                
                # 添加连接记忆
                print("\n【步骤6】添加连接记忆")
                mem_id4 = await mem.add_memory("2024年距离阿里巴巴成立的1999年已经过去了25年")
                print(f"  添加记忆: {mem_id4}")
                
                # 再次查询
                relations_2024_new = await mem.get_entity_relations("2024年")
                relations_1999_new = await mem.get_entity_relations("1999年")
                
                print(f"\n  更新后的关系:")
                print(f"    '2024年' 关系数: {len(relations_2024_new)}")
                print(f"    '1999年' 关系数: {len(relations_1999_new)}")
                
                # 查找新路径
                paths_new = mem.knowledge_graph.query_path(entity_2024_id, entity_1999_id, max_depth=3)
                if paths_new:
                    print(f"\n  添加连接记忆后，找到 {len(paths_new)} 条路径:")
                    for i, path in enumerate(paths_new):
                        print(f"    路径 {i+1}: {' -> '.join([p[:10] + '...' for p in path])}")
    
    else:
        print("  未找到指定的实体")
    
    # 保存并清理
    await mem.save_knowledge_graph()
    await mem.flush()
    mem.close()
    
    shutil.rmtree(test_dir, ignore_errors=True)
    print("\n=== 演示完成 ===")


if __name__ == "__main__":
    asyncio.run(demo_entity_relation_query())
