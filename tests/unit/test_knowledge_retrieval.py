"""知识检索模块单元测试

V2新增功能：领域知识检索、相似度匹配、上下文注入
"""

import pytest


class TestKnowledgeRetrievalBasics:
    """知识检索基础功能测试"""

    def test_create_knowledge_retriever(self):
        """测试：创建知识检索器"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        assert retriever is not None

    def test_add_knowledge_entry(self):
        """测试：添加知识条目"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        entry_id = retriever.add_knowledge(
            domain="AT_支付域",
            content="支付回调处理流程：签名验证→状态更新→通知业务",
            tags=["支付", "回调", "流程"]
        )

        assert entry_id is not None
        assert entry_id.startswith("knowledge_")

    def test_knowledge_entry_has_attributes(self):
        """测试：知识条目具有属性"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        entry_id = retriever.add_knowledge(
            domain="AT_支付域",
            content="测试内容",
            tags=["测试"]
        )

        entry = retriever.get_knowledge(entry_id)
        assert entry.domain == "AT_支付域"
        assert entry.content == "测试内容"
        assert entry.tags == ["测试"]


class TestDomainRetrieval:
    """领域检索测试"""

    def test_retrieve_by_domain(self):
        """测试：按领域检索知识"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        retriever.add_knowledge(domain="AT_支付域", content="支付知识1", tags=["支付"])
        retriever.add_knowledge(domain="AT_支付域", content="支付知识2", tags=["退款"])
        retriever.add_knowledge(domain="DA_订单域", content="订单知识", tags=["订单"])

        results = retriever.retrieve_by_domain("AT_支付域")
        assert len(results) == 2
        assert all(e.domain == "AT_支付域" for e in results)

    def test_retrieve_by_tag(self):
        """测试：按标签检索知识"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        retriever.add_knowledge(domain="AT_支付域", content="支付回调", tags=["回调", "支付"])
        retriever.add_knowledge(domain="DA_订单域", content="订单回调", tags=["回调", "订单"])
        retriever.add_knowledge(domain="FM_会员域", content="会员积分", tags=["积分"])

        results = retriever.retrieve_by_tag("回调")
        assert len(results) == 2
        assert all("回调" in e.tags for e in results)

    def test_retrieve_by_domain_and_tag(self):
        """测试：按领域和标签联合检索"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        retriever.add_knowledge(domain="AT_支付域", content="支付回调", tags=["回调"])
        retriever.add_knowledge(domain="AT_支付域", content="支付退款", tags=["退款"])
        retriever.add_knowledge(domain="DA_订单域", content="订单回调", tags=["回调"])

        results = retriever.retrieve(domain="AT_支付域", tags=["回调"])
        assert len(results) == 1
        assert results[0].content == "支付回调"

    def test_no_match_returns_empty_list(self):
        """测试：无匹配返回空列表"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        retriever.add_knowledge(domain="AT_支付域", content="支付知识", tags=["支付"])

        results = retriever.retrieve_by_domain("FM_会员域")
        assert results == []


class TestSimilarityMatching:
    """相似度匹配测试"""

    def test_search_by_keywords(self):
        """测试：关键词搜索"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        retriever.add_knowledge(domain="AT_支付域", content="支付回调处理流程详解", tags=["回调"])
        retriever.add_knowledge(domain="AT_支付域", content="退款处理流程", tags=["退款"])
        retriever.add_knowledge(domain="DA_订单域", content="订单创建流程", tags=["订单"])

        # 搜索包含"处理流程"的知识
        results = retriever.search("处理流程")
        assert len(results) >= 2

    def test_search_with_limit(self):
        """测试：限制搜索结果数量"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        for i in range(10):
            retriever.add_knowledge(
                domain="AT_支付域",
                content=f"支付知识{i}",
                tags=["支付"]
            )

        results = retriever.search("支付", limit=5)
        assert len(results) <= 5


class TestKnowledgeContext:
    """知识上下文注入测试"""

    def test_build_context_for_task(self):
        """测试：为任务构建上下文"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        retriever.add_knowledge(
            domain="AT_支付域",
            content="支付回调必须验签",
            tags=["回调", "安全"]
        )
        retriever.add_knowledge(
            domain="AT_支付域",
            content="退款需检查订单状态",
            tags=["退款"]
        )

        context = retriever.build_context(domain="AT_支付域")
        assert "支付回调必须验签" in context
        assert "退款需检查订单状态" in context

    def test_empty_context_when_no_knowledge(self):
        """测试：无知识时返回空上下文"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        context = retriever.build_context(domain="FM_会员域")
        assert context == ""


class TestKnowledgeStatistics:
    """知识统计测试"""

    def test_get_total_count(self):
        """测试：获取知识总数"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        retriever.add_knowledge(domain="AT_支付域", content="知识1", tags=["a"])
        retriever.add_knowledge(domain="DA_订单域", content="知识2", tags=["b"])

        count = retriever.get_total_count()
        assert count == 2

    def test_get_domain_count(self):
        """测试：获取领域知识数量"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        retriever.add_knowledge(domain="AT_支付域", content="知识1", tags=["a"])
        retriever.add_knowledge(domain="AT_支付域", content="知识2", tags=["b"])
        retriever.add_knowledge(domain="DA_订单域", content="知识3", tags=["c"])

        count = retriever.get_domain_count("AT_支付域")
        assert count == 2

    def test_list_all_domains(self):
        """测试：列出所有领域"""
        from claudeflow.legacy.knowledge_retrieval import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        retriever.add_knowledge(domain="AT_支付域", content="知识1", tags=["a"])
        retriever.add_knowledge(domain="DA_订单域", content="知识2", tags=["b"])
        retriever.add_knowledge(domain="FM_会员域", content="知识3", tags=["c"])

        domains = retriever.list_domains()
        assert "AT_支付域" in domains
        assert "DA_订单域" in domains
        assert "FM_会员域" in domains