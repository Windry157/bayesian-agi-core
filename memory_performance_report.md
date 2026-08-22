# 记忆系统性能测试报告

> 测试时间: 2026-05-15T01:55:21.606528
> 测试环境: win32 - Python 3.13.12

---

## 摘要

本报告提供了 Bayesian-AGI-Core 记忆系统的全面性能评估。

### 关键指标

- **添加性能**: 约 85.65 项/秒
- **检索性能**: 约 2368.46 查询/秒
- **存储效率**: 约 118.3%

---

## 测试详情

### 1. 基础添加性能测试

**测试**: 添加 100 个记忆项

| 指标 | 数值 |
|-----|-----|
| 平均时间 | 11.68 ms |
| 中位数时间 | 11.02 ms |
| 最大时间 | 47.03 ms |
| 最小时间 | 8.37 ms |
| 标准差 | 4.46 ms |
| 吞吐量 | 85.65 项/秒 |

### 2. 基础检索性能测试

**测试**: 在 100 个记忆项中进行 100 次检索

| 指标 | 数值 |
|-----|-----|
| 平均时间 | 0.42 ms |
| 中位数时间 | 0.33 ms |
| 最大时间 | 4.72 ms |
| 最小时间 | 0.32 ms |
| 标准差 | 0.50 ms |
| 吞吐量 | 2368.46 查询/秒 |

### 3. 层级性能对比

| 层级 | 平均时间 (ms) | 吞吐量 (项/秒) |
|-----|------|-----|
| short_term | 10.58 | 94.53 |
| medium_term | 13.49 | 74.12 |
| long_term | 10.28 | 97.28 |

### 4. 可扩展性测试

| 数据规模 | 添加平均时间 (ms) | 检索平均时间 (ms) |
|--------|-----------------|-----------------|
| 10 | 11.85 | 0.05 |
| 50 | 12.90 | 0.20 |
| 100 | 14.34 | 0.39 |
| 200 | 11.52 | 0.79 |
| 500 | 14.73 | 2.05 |

### 5. 存储效率

**测试**: 200 个记忆项

| 指标 | 数值 |
|-----|-----|
| 存储文件大小 | 138,230 字节 (134.99 KB) |
| 内容总大小 | 116,816 字节 (114.08 KB) |
| 存储效率 | 118.3% |
| 平均每项大小 | 691.15 字节/项 |

---

## 优化建议

基于测试结果，我们建议以下优化：

1. **性能优化**:
   - 当前添加和检索性能已可接受，但可进一步优化
   - 添加 85.65 项/秒
   - 检索 2368.46 查询/秒

2. **存储优化**:
   - 当前存储效率为 118.3%
   - 可考虑压缩或优化 JSON 存储

3. **可扩展性**:
   - 在 500 个记忆项时仍保持良好性能
   - 建议实施批量操作和索引优化

4. **索引优化**:
   - 当前使用 TF-IDF 索引
   - 可考虑迁移到 ChromaDB 或其他向量数据库

---

## 结论

记忆系统当前性能表现良好，能够满足基本使用需求。如需支持大规模数据，建议实施优化措施。

---

## 附录: 原始数据

```json
{
  "baseline_add": {
    "num_items": 100,
    "avg_time_ms": 11.675324440002441,
    "median_time_ms": 11.022329330444336,
    "max_time_ms": 47.03044891357422,
    "min_time_ms": 8.371591567993164,
    "std_dev_ms": 4.462987314608188,
    "throughput_items_per_sec": 85.65072475191883
  },
  "baseline_search": {
    "num_items": 100,
    "num_queries": 100,
    "avg_time_ms": 0.42221546173095703,
    "median_time_ms": 0.3286600112915039,
    "max_time_ms": 4.718780517578125,
    "min_time_ms": 0.3235340118408203,
    "std_dev_ms": 0.5019829202958485,
    "throughput_queries_per_sec": 2368.4589756620926
  },
  "layer_performance": {
    "short_term": {
      "num_items": 50,
      "avg_time_ms": 10.578370094299316,
      "median_time_ms": 10.857582092285156,
      "max_time_ms": 14.885663986206055,
      "min_time_ms": 0.7741451263427734,
      "std_dev_ms": 2.1206909052915828,
      "throughput_items_per_sec": 94.53252165368085
    },
    "medium_term": {
      "num_items": 50,
      "avg_time_ms": 13.49194049835205,
      "median_time_ms": 13.696551322937012,
      "max_time_ms": 18.25237274169922,
      "min_time_ms": 3.080129623413086,
      "std_dev_ms": 2.0821174018241266,
      "throughput_items_per_sec": 74.11832272178663
    },
    "long_term": {
      "num_items": 50,
      "avg_time_ms": 10.27916431427002,
      "median_time_ms": 10.89167594909668,
      "max_time_ms": 15.692472457885742,
      "min_time_ms": 0.8018016815185547,
      "std_dev_ms": 1.9134798688016887,
      "throughput_items_per_sec": 97.28417305400527
    }
  },
  "scalability": {
    "size_10": {
      "add": {
        "num_items": 10,
        "avg_time_ms": 11.849522590637207,
        "median_time_ms": 13.351082801818848,
        "max_time_ms": 13.87166976928711,
        "min_time_ms": 0.8101463317871094,
        "std_dev_ms": 3.9865799630408985,
        "throughput_items_per_sec": 84.39158559773041
      },
      "search": {
        "num_items": 10,
        "num_queries": 100,
        "avg_time_ms": 0.05137443542480469,
        "median_time_ms": 0.035762786865234375,
        "max_time_ms": 1.514434814453125,
        "min_time_ms": 0.03504753112792969,
        "std_dev_ms": 0.14782909929063182,
        "throughput_queries_per_sec": 19464.934100612587
      }
    },
    "size_50": {
      "add": {
        "num_items": 50,
        "avg_time_ms": 12.898807525634766,
        "median_time_ms": 10.993599891662598,
        "max_time_ms": 105.85498809814453,
        "min_time_ms": 0.9493827819824219,
        "std_dev_ms": 14.167751650627157,
        "throughput_items_per_sec": 77.52654638908483
      },
      "search": {
        "num_items": 50,
        "num_queries": 100,
        "avg_time_ms": 0.20441293716430664,
        "median_time_ms": 0.16701221466064453,
        "max_time_ms": 2.237081527709961,
        "min_time_ms": 0.1633167266845703,
        "std_dev_ms": 0.21154933666742082,
        "throughput_queries_per_sec": 4892.058271224792
      }
    },
    "size_100": {
      "add": {
        "num_items": 100,
        "avg_time_ms": 14.344570636749268,
        "median_time_ms": 14.143586158752441,
        "max_time_ms": 29.388904571533203,
        "min_time_ms": 0.7708072662353516,
        "std_dev_ms": 2.783749166978512,
        "throughput_items_per_sec": 69.7127871808241
      },
      "search": {
        "num_items": 100,
        "num_queries": 100,
        "avg_time_ms": 0.39465904235839844,
        "median_time_ms": 0.32901763916015625,
        "max_time_ms": 2.7496814727783203,
        "min_time_ms": 0.3230571746826172,
        "std_dev_ms": 0.3426888775543256,
        "throughput_queries_per_sec": 2533.832733247952
      }
    },
    "size_200": {
      "add": {
        "num_items": 200,
        "avg_time_ms": 11.5237295627594,
        "median_time_ms": 11.632084846496582,
        "max_time_ms": 17.666339874267578,
        "min_time_ms": 0.8223056793212891,
        "std_dev_ms": 1.934295647679923,
        "throughput_items_per_sec": 86.77746163287664
      },
      "search": {
        "num_items": 200,
        "num_queries": 100,
        "avg_time_ms": 0.7868576049804688,
        "median_time_ms": 0.6630420684814453,
        "max_time_ms": 3.4444332122802734,
        "min_time_ms": 0.6461143493652344,
        "std_dev_ms": 0.49551512192319014,
        "throughput_queries_per_sec": 1270.8779754690454
      }
    },
    "size_500": {
      "add": {
        "num_items": 500,
        "avg_time_ms": 14.728630065917969,
        "median_time_ms": 14.227867126464844,
        "max_time_ms": 73.10867309570312,
        "min_time_ms": 0.9267330169677734,
        "std_dev_ms": 5.2328166032912256,
        "throughput_items_per_sec": 67.89497702939792
      },
      "search": {
        "num_items": 500,
        "num_queries": 100,
        "avg_time_ms": 2.049241065979004,
        "median_time_ms": 1.674652099609375,
        "max_time_ms": 5.316019058227539,
        "min_time_ms": 1.6279220581054688,
        "std_dev_ms": 0.8534637762416875,
        "throughput_queries_per_sec": 487.9855360122116
      }
    }
  },
  "efficiency": {
    "file_size_bytes": 138230,
    "content_size_bytes": 116816,
    "efficiency_percent": 118.33139295986852,
    "avg_item_size_bytes": 691.15
  }
}
```
