"""知识检索模块 - 领域知识检索与上下文注入

V2核心功能：领域知识管理、相似度匹配、上下文构建
"""

import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class KnowledgeEntry:
    """知识条目数据模型"""
    id: str
    domain: str
    content: str
    tags: List[str] = field(default_factory=list)
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()


class KnowledgeRetriever:
    """知识检索器"""

    def __init__(self):
        """初始化知识检索器"""
        self._knowledge_store: Dict[str, KnowledgeEntry] = {}
        self._domain_index: Dict[str, List[str]] = {}  # domain -> [entry_ids]
        self._tag_index: Dict[str, List[str]] = {}  # tag -> [entry_ids]

    def add_knowledge(
        self,
        domain: str,
        content: str,
        tags: List[str] = None
    ) -> str:
        """
        添加知识条目

        Args:
            domain: 业务领域
            content: 知识内容
            tags: 标签列表

        Returns:
            知识条目ID
        """
        if tags is None:
            tags = []

        entry_id = f"knowledge_{uuid.uuid4().hex[:8]}"

        entry = KnowledgeEntry(
            id=entry_id,
            domain=domain,
            content=content,
            tags=tags
        )

        # 存储条目
        self._knowledge_store[entry_id] = entry

        # 更新领域索引
        if domain not in self._domain_index:
            self._domain_index[domain] = []
        self._domain_index[domain].append(entry_id)

        # 更新标签索引
        for tag in tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(entry_id)

        return entry_id

    def get_knowledge(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """
        获取知识条目

        Args:
            entry_id: 知识条目ID

        Returns:
            知识条目，不存在返回None
        """
        return self._knowledge_store.get(entry_id)

    def retrieve_by_domain(self, domain: str) -> List[KnowledgeEntry]:
        """
        按领域检索知识

        Args:
            domain: 业务领域

        Returns:
            匹配的知识条目列表
        """
        entry_ids = self._domain_index.get(domain, [])
        return [self._knowledge_store[id] for id in entry_ids]

    def retrieve_by_tag(self, tag: str) -> List[KnowledgeEntry]:
        """
        按标签检索知识

        Args:
            tag: 标签

        Returns:
            匹配的知识条目列表
        """
        entry_ids = self._tag_index.get(tag, [])
        return [self._knowledge_store[id] for id in entry_ids]

    def retrieve(
        self,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[KnowledgeEntry]:
        """
        联合检索知识

        Args:
            domain: 业务领域（可选）
            tags: 标签列表（可选）

        Returns:
            匹配的知识条目列表
        """
        if domain is None and tags is None:
            return list(self._knowledge_store.values())

        # 按领域筛选
        if domain:
            candidates = set(self._domain_index.get(domain, []))
        else:
            candidates = set(self._knowledge_store.keys())

        # 按标签筛选
        if tags:
            for tag in tags:
                tag_entries = set(self._tag_index.get(tag, []))
                candidates = candidates & tag_entries

        return [self._knowledge_store[id] for id in candidates]

    def search(self, query: str, limit: int = 10) -> List[KnowledgeEntry]:
        """
        关键词搜索知识

        Args:
            query: 搜索关键词
            limit: 结果数量限制

        Returns:
            匹配的知识条目列表
        """
        results = []
        query_lower = query.lower()

        for entry in self._knowledge_store.values():
            # 检查内容是否包含关键词
            if query_lower in entry.content.lower():
                results.append(entry)
            # 检查标签是否匹配
            elif any(query_lower in tag.lower() for tag in entry.tags):
                results.append(entry)

        return results[:limit]

    def build_context(self, domain: str) -> str:
        """
        为任务构建知识上下文

        Args:
            domain: 业务领域

        Returns:
            格式化的知识上下文字符串
        """
        entries = self.retrieve_by_domain(domain)

        if not entries:
            return ""

        context_parts = []
        for entry in entries:
            context_parts.append(f"- [{entry.tags}] {entry.content}")

        return "\n".join(context_parts)

    def get_total_count(self) -> int:
        """获取知识总数"""
        return len(self._knowledge_store)

    def get_domain_count(self, domain: str) -> int:
        """获取领域知识数量"""
        return len(self._domain_index.get(domain, []))

    def list_domains(self) -> List[str]:
        """列出所有领域"""
        return list(self._domain_index.keys())

    def remove_knowledge(self, entry_id: str):
        """
        删除知识条目

        Args:
            entry_id: 知识条目ID
        """
        entry = self._knowledge_store.get(entry_id)
        if entry:
            # 从存储中删除
            self._knowledge_store.pop(entry_id, None)

            # 从领域索引中删除
            if entry.domain in self._domain_index:
                self._domain_index[entry.domain] = [
                    id for id in self._domain_index[entry.domain]
                    if id != entry_id
                ]

            # 从标签索引中删除
            for tag in entry.tags:
                if tag in self._tag_index:
                    self._tag_index[tag] = [
                        id for id in self._tag_index[tag]
                        if id != entry_id
                    ]