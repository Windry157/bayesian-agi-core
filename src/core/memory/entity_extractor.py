#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体抽取模块
使用增强规则引擎和LLM进行实体识别
"""

import logging
import re
from typing import List, Dict, Any, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import spacy
    HAS_SPACY = True
    try:
        nlp = spacy.load("zh_core_web_sm")
    except:
        nlp = None
        logger.warning("spaCy 中文模型未安装，将使用增强规则引擎")
except ImportError:
    HAS_SPACY = False
    nlp = None
    logger.warning("spaCy 未安装，将使用增强规则引擎")


MAX_TEXT_LENGTH = 10000
CHUNK_OVERLAP = 200


class EntityExtractor:
    """实体抽取器
    支持多种实体类型的识别：人名、地名、组织、时间、数字等
    使用增强规则引擎和可选LLM进行实体识别
    """
    
    ENTITY_TYPES = {
        "PERSON": "人名",
        "GPE": "地名/国家",
        "ORG": "组织/公司",
        "DATE": "日期",
        "TIME": "时间",
        "NUM": "数字",
        "EVENT": "事件",
        "PRODUCT": "产品",
        "CONCEPT": "概念",
        "EMAIL": "邮箱",
        "URL": "网址",
        "PHONE": "电话",
        "MONEY": "金额",
        "PERCENT": "百分比"
    }
    
    def __init__(self):
        self.use_spacy = HAS_SPACY and nlp is not None
        self._init_patterns()
    
    def _init_patterns(self):
        """初始化增强的规则模式"""
        # 中文姓氏列表
        self.CHINESE_SURNAMES = [
            "张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴",
            "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "高", "罗",
            "郑", "梁", "谢", "宋", "唐", "许", "邓", "冯", "韩", "曹",
            "曾", "彭", "萧", "蔡", "潘", "田", "董", "袁", "于", "余",
            "叶", "蒋", "杜", "苏", "魏", "程", "吕", "丁", "沈", "任",
            "姚", "卢", "傅", "钟", "姜", "崔", "谭", "廖", "范", "汪",
            "陆", "金", "石", "戴", "贾", "韦", "夏", "邱", "方", "侯",
            "邹", "熊", "孟", "秦", "白", "江", "阎", "薛", "尹", "段",
            "雷", "黎", "史", "龙", "贺", "顾", "毛", "郝", "龚", "邵",
            "万", "钱", "严", "覃", "武", "戴", "莫", "孔", "向", "汤",
            "欧阳", "太史", "端木", "上官", "司马", "东方", "独孤", "南宫",
            "万俟", "闻人", "夏侯", "诸葛", "尉迟", "公羊", "赫连", "澹台",
            "皇甫", "宗政", "濮阳", "淳于", "单于", "太叔", "申屠", "公孙",
            "仲孙", "轩辕", "令狐", "钟离", "宇文", "长孙", "慕容", "鲜于",
            "闾丘", "司徒", "司空", "亓官", "司寇", "颛孙", "端木", "巫马",
            "公西", "漆雕", "乐正", "壤驷", "公良", "拓跋", "夹谷", "宰父",
            "谷梁", "晋", "楚", "闫", "法", "汝", "鄢", "涂", "钦", "段干",
            "百里", "东郭", "南门", "呼延", "归海", "羊舌", "微生", "岳",
            "缑", "亢", "况", "后", "有", "琴", "梁丘", "左丘", "东门",
            "西门", "南荣", "东里", "东宫", "仲长", "子车", "亓官", "司寇",
            "巫马", "公西", "颛孙", "壤驷", "公良", "漆雕", "乐正", "宰父",
            "谷梁", "段干", "百里", "东郭", "南郭"
        ]
        
        # 中国省份、直辖市、自治区
        self.CHINESE_PROVINCES = [
            "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林",
            "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
            "湖北", "湖南", "广东", "广西", "海南", "四川", "贵州", "云南",
            "陕西", "甘肃", "青海", "内蒙古", "新疆", "西藏", "宁夏", "台湾",
            "香港", "澳门"
        ]
        
        # 常见城市后缀
        self.CITY_SUFFIXES = ["市", "县", "区", "省", "州", "府", "路", "道", "都", "城", "镇", "乡", "村"]
        
        # 组织后缀
        self.ORG_SUFFIXES = [
            "公司", "集团", "有限公司", "股份公司", "企业", "工厂", "厂",
            "大学", "学院", "学校", "研究院", "研究所", "中心", "实验室",
            "医院", "卫生院", "政府", "局", "厅", "部", "委员会", "协会",
            "学会", "基金会", "联盟", "合作社", "银行", "保险公司", "证券公司",
            "出版社", "电视台", "电台", "报社", "杂志社", "网站", "网络",
            "团队", "组织", "机构", "部门", "处", "科", "室"
        ]
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """从文本中抽取实体（支持超长文本分块处理）
        
        Args:
            text: 输入文本
            
        Returns:
            实体列表，每个实体包含 type, text, start, end
        """
        if len(text) > MAX_TEXT_LENGTH:
            return self._extract_chunked(text)

        entities = []
        
        if self.use_spacy:
            entities.extend(self._extract_with_spacy(text))
        
        # 增强规则引擎
        entities.extend(self._extract_with_enhanced_rules(text))
        
        # 去重
        unique_entities = self._deduplicate_entities(entities)
        
        logger.info(f"实体抽取完成: 文本长度={len(text)}, 抽取到{len(unique_entities)}个实体")
        return unique_entities

    def _extract_chunked(self, text: str) -> List[Dict[str, Any]]:
        """将超长文本分块抽取实体"""
        all_entities = []
        chunk_size = MAX_TEXT_LENGTH // 2
        start = 0
        chunk_idx = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                adjust = text.rfind("。", start, end)
                if adjust > start + chunk_size // 2:
                    end = adjust + 1
            chunk = text[start:end]
            chunk_entities = []
            if self.use_spacy:
                chunk_entities.extend(self._extract_with_spacy(chunk))
            chunk_entities.extend(self._extract_with_enhanced_rules(chunk))
            for ent in chunk_entities:
                ent["start"] += start
                ent["end"] += start
            all_entities.extend(chunk_entities)
            chunk_idx += 1
            start = end - CHUNK_OVERLAP if end < len(text) else end
        unique_entities = self._deduplicate_entities(all_entities)
        logger.info(f"实体抽取完成(分块): 文本长度={len(text)}, 分块数={chunk_idx}, 抽取到{len(unique_entities)}个实体")
        return unique_entities
    
    def _extract_with_spacy(self, text: str) -> List[Dict[str, Any]]:
        """使用spaCy抽取实体"""
        entities = []
        try:
            doc = nlp(text)
            for ent in doc.ents:
                entities.append({
                    "type": ent.label_,
                    "type_name": self.ENTITY_TYPES.get(ent.label_, ent.label_),
                    "text": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "source": "spacy"
                })
        except Exception as e:
            logger.error(f"spaCy实体抽取失败: {e}")
        return entities
    
    def _extract_with_enhanced_rules(self, text: str) -> List[Dict[str, Any]]:
        """使用增强规则引擎抽取实体"""
        entities = []
        
        # 1. 日期匹配（增强）
        entities.extend(self._extract_dates(text))
        
        # 2. 时间匹配（增强）
        entities.extend(self._extract_times(text))
        
        # 3. 数字和金额匹配
        entities.extend(self._extract_numbers(text))
        
        # 4. 人名匹配
        entities.extend(self._extract_persons(text))
        
        # 5. 地名匹配
        entities.extend(self._extract_places(text))
        
        # 6. 组织匹配
        entities.extend(self._extract_organizations(text))
        
        # 7. 联系方式匹配
        entities.extend(self._extract_contacts(text))
        
        # 8. 网址和邮箱
        entities.extend(self._extract_urls_emails(text))
        
        return entities
    
    def _extract_dates(self, text: str) -> List[Dict[str, Any]]:
        """抽取日期实体"""
        entities = []
        
        date_patterns = [
            # 完整日期格式
            (r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日号]?', "DATE"),
            # 年月格式
            (r'(\d{4})年(\d{1,2})月', "DATE"),
            # 月日格式
            (r'(\d{1,2})月(\d{1,2})日', "DATE"),
            # 年份
            (r'(\d{4})年', "DATE"),
            # 相对日期
            (r'今天|明天|后天|昨天|前天|大前天|大后天', "DATE"),
            (r'本周|上周|下周|本月|上月|下月|今年|去年|明年', "DATE"),
            # 星期
            (r'星期[一二三四五六日天]|周[一二三四五六日天]', "DATE"),
            # 节日
            (r'春节|元旦|清明节|劳动节|端午节|中秋节|国庆节|圣诞节', "DATE"),
        ]
        
        for pattern, entity_type in date_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    "type": entity_type,
                    "type_name": self.ENTITY_TYPES.get(entity_type, entity_type),
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "source": "rule"
                })
        
        return entities
    
    def _extract_times(self, text: str) -> List[Dict[str, Any]]:
        """抽取时间实体"""
        entities = []
        
        time_patterns = [
            # 标准时间格式
            (r'(\d{1,2}):(\d{2})(:\d{2})?', "TIME"),
            # 中文时间格式
            (r'(\d{1,2})点(\d{2})?分?(\d{2})?秒?', "TIME"),
            (r'上午(\d{1,2}):?(\d{2})?分?', "TIME"),
            (r'下午(\d{1,2}):?(\d{2})?分?', "TIME"),
            (r'晚上(\d{1,2}):?(\d{2})?分?', "TIME"),
            (r'凌晨(\d{1,2}):?(\d{2})?分?', "TIME"),
            (r'中午(\d{1,2}):?(\d{2})?分?', "TIME"),
            # 相对时间
            (r'现在|刚才|刚刚|马上|立刻|稍后|一会儿', "TIME"),
        ]
        
        for pattern, entity_type in time_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    "type": entity_type,
                    "type_name": self.ENTITY_TYPES.get(entity_type, entity_type),
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "source": "rule"
                })
        
        return entities
    
    def _extract_numbers(self, text: str) -> List[Dict[str, Any]]:
        """抽取数字、金额、百分比实体"""
        entities = []
        
        # 金额匹配
        money_patterns = [
            (r'[¥$€£] ?\d+(\.\d+)?[万亿十亿千万百万十万]?', "MONEY"),
            (r'\d+(\.\d+)?[万亿十亿千万百万十万]?[元块美元欧元英镑]', "MONEY"),
        ]
        
        for pattern, entity_type in money_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    "type": entity_type,
                    "type_name": self.ENTITY_TYPES.get(entity_type, entity_type),
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "source": "rule"
                })
        
        # 百分比匹配
        for match in re.finditer(r'\d+(\.\d+)?%', text):
            entities.append({
                "type": "PERCENT",
                "type_name": "百分比",
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "source": "rule"
            })
        
        # 普通数字匹配（避免与金额重复）
        for match in re.finditer(r'\b\d+(\.\d+)?\b', text):
            entities.append({
                "type": "NUM",
                "type_name": "数字",
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "source": "rule"
            })
        
        return entities
    
    def _extract_persons(self, text: str) -> List[Dict[str, Any]]:
        """抽取人名实体"""
        entities = []
        person_non_name_chars = set("这在到从对把被将与和跟为由以用通过于及其或还是的能会要可已经正在了是")
        
        for surname in sorted(self.CHINESE_SURNAMES, key=lambda x: -len(x)):
            for match in re.finditer(re.escape(surname), text):
                name_start = match.start()
                # 左边界检查：前面不应是中文（除非在开头或标点后）
                if name_start > 0:
                    prev = text[name_start - 1]
                    if '\u4e00' <= prev <= '\u9fff' and prev not in "·" and prev not in "，。、；：？！\n\r\t ":
                        continue
                
                # 向后看2-3个字组成人名
                name_end = match.end()
                name_chars = 0
                for ch in text[name_end:]:
                    if '\u4e00' <= ch <= '\u9fff' and name_chars < 3:
                        if ch in person_non_name_chars:
                            break
                        name_end += 1
                        name_chars += 1
                    else:
                        break
                name = text[name_start:name_end]
                if len(name) < 2 or len(name) > 4:
                    continue
                if any(name.endswith(s) for s in self.ORG_SUFFIXES + self.CITY_SUFFIXES):
                    continue
                entities.append({
                    "type": "PERSON",
                    "type_name": "人名",
                    "text": name,
                    "start": name_start,
                    "end": name_end,
                    "source": "rule"
                })
        
        return entities
    
    def _extract_places(self, text: str) -> List[Dict[str, Any]]:
        """抽取地名实体"""
        entities = []
        
        # 匹配省份
        for province in self.CHINESE_PROVINCES:
            for match in re.finditer(re.escape(province), text):
                entities.append({
                    "type": "GPE",
                    "type_name": "地名/国家",
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "source": "rule"
                })
        
        # 匹配带后缀的城市名
        for suffix in self.CITY_SUFFIXES:
            for m in re.finditer(re.escape(suffix), text):
                end = m.end()
                suffix_start = m.start()
                found = None
                for name_len in range(2, 6):
                    start = suffix_start - name_len
                    if start < 0:
                        break
                    if all('\u4e00' <= text[i] <= '\u9fff' for i in range(start, suffix_start)):
                        found = (start, name_len)
                        break
                if found is None:
                    continue
                start, name_len = found
                name = text[start:start + name_len] + suffix
                entities.append({
                    "type": "GPE",
                    "type_name": "地名/国家",
                    "text": name,
                    "start": start,
                    "end": end,
                    "source": "rule"
                })
        
        return entities
    
    def _extract_organizations(self, text: str) -> List[Dict[str, Any]]:
        """抽取组织实体"""
        entities = []
        left_delimiters = set("在向到从对把被将与和跟为由以用通过、，。；：？！\n\r\t（）()【】[]{}「」『』\"' ")
        
        for suffix in sorted(self.ORG_SUFFIXES, key=lambda x: -len(x)):
            for m in re.finditer(re.escape(suffix), text):
                end = m.end()
                suffix_start = m.start()
                # 从左到右扫描：尝试[2,10]个中文字符，找到第一个有效左边界
                found = None
                for name_len in range(2, 11):
                    start = suffix_start - name_len
                    if start < 0:
                        break
                    # 检查 start 到 suffix_start 是否全是中文
                    if all('\u4e00' <= text[i] <= '\u9fff' for i in range(start, suffix_start)):
                        # 检查左边界
                        if start == 0:
                            found = (start, name_len)
                            break
                        is_chinese = '\u4e00' <= text[start-1] <= '\u9fff'
                        if not is_chinese or text[start-1] in left_delimiters:
                            found = (start, name_len)
                            break
                if found is None:
                    continue
                start, name_len = found
                name = text[start:start + name_len] + suffix
                entities.append({
                    "type": "ORG",
                    "type_name": "组织/公司",
                    "text": name,
                    "start": start,
                    "end": end,
                    "source": "rule"
                })
        
        return entities
    
    def _extract_contacts(self, text: str) -> List[Dict[str, Any]]:
        """抽取联系方式实体"""
        entities = []
        
        # 手机号
        phone_pattern = r'1[3-9]\d{9}'
        for match in re.finditer(phone_pattern, text):
            entities.append({
                "type": "PHONE",
                "type_name": "电话",
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "source": "rule"
            })
        
        # 固定电话
        landline_pattern = r'0\d{2,3}-?\d{7,8}'
        for match in re.finditer(landline_pattern, text):
            entities.append({
                "type": "PHONE",
                "type_name": "电话",
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "source": "rule"
            })
        
        return entities
    
    def _extract_urls_emails(self, text: str) -> List[Dict[str, Any]]:
        """抽取网址和邮箱实体"""
        entities = []
        
        # 邮箱
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        for match in re.finditer(email_pattern, text):
            entities.append({
                "type": "EMAIL",
                "type_name": "邮箱",
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "source": "rule"
            })
        
        # 网址
        url_pattern = r'(https?://)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/[^\s]*)?'
        for match in re.finditer(url_pattern, text):
            entities.append({
                "type": "URL",
                "type_name": "网址",
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "source": "rule"
            })
        
        return entities
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复实体，优先保留更好的来源"""
        # 类型优先级（数字越小优先级越高）
        type_priority = {
            "PHONE": 0, "EMAIL": 1, "URL": 2, "MONEY": 3, "PERCENT": 4,
            "PERSON": 5, "ORG": 6,
            "GPE": 7,
            "DATE": 8, "TIME": 9, "NUM": 10, "CONCEPT": 11,
        }
        
        # 按起始位置升序、长度降序排序
        sorted_ents = sorted(entities, key=lambda e: (e["start"], -(e["end"] - e["start"])))
        
        kept = []
        for ent in sorted_ents:
            # 检查是否与已保留的实体重叠
            overlap = False
            for k in kept:
                if not (ent["end"] <= k["start"] or ent["start"] >= k["end"]):
                    overlap = True
                    # 如果重叠，保留优先级更高的类型
                    ent_pri = type_priority.get(ent["type"], 99)
                    k_pri = type_priority.get(k["type"], 99)
                    if ent_pri < k_pri:
                        # 新实体优先级更高，替换
                        kept.remove(k)
                        kept.append(ent)
                    break
            if not overlap:
                kept.append(ent)
        
        # 对相同起始+文本的去重
        seen = {}
        for ent in kept:
            key = (ent["text"], ent["start"])
            if key not in seen:
                seen[key] = ent
            else:
                existing = seen[key]
                if existing["source"] == "rule" and ent["source"] != "rule":
                    seen[key] = ent
        
        return list(seen.values())
    
    def classify_entity(self, entity_text: str) -> str:
        """对实体进行分类"""
        entity_text = entity_text.strip()
        
        # 日期判断
        if re.search(r'\d{4}[-/年]', entity_text) or entity_text in ["今天", "明天", "昨天"]:
            return "DATE"
        
        # 时间判断
        if re.search(r'\d{1,2}:', entity_text) or "点" in entity_text or entity_text in ["现在", "刚才"]:
            return "TIME"
        
        # 邮箱判断
        if "@" in entity_text and "." in entity_text:
            return "EMAIL"
        
        # 网址判断
        if entity_text.startswith(("http://", "https://", "www.")):
            return "URL"
        
        # 电话判断
        if re.match(r'1[3-9]\d{9}', entity_text) or re.match(r'0\d{2,3}-?\d{7,8}', entity_text):
            return "PHONE"
        
        # 金额判断
        if any(symbol in entity_text for symbol in ["¥", "$", "€", "£", "元", "块"]):
            return "MONEY"
        
        # 百分比判断
        if "%" in entity_text:
            return "PERCENT"
        
        # 数字判断
        if re.match(r'^\d+(\.\d+)?$', entity_text):
            return "NUM"
        
        # 人名判断
        for surname in self.CHINESE_SURNAMES:
            if entity_text.startswith(surname) and 2 <= len(entity_text) <= 4:
                return "PERSON"
        
        # 组织判断
        for suffix in self.ORG_SUFFIXES:
            if entity_text.endswith(suffix):
                return "ORG"
        
        # 地名判断
        for province in self.CHINESE_PROVINCES:
            if entity_text == province or entity_text.startswith(province):
                return "GPE"
        for suffix in self.CITY_SUFFIXES:
            if entity_text.endswith(suffix):
                return "GPE"
        
        return "CONCEPT"


# 全局实体抽取器实例
entity_extractor = EntityExtractor()
