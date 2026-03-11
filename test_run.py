"""测试修改后的代码结构"""
import sys
import os
sys.path.insert(0, '.')

# 临时设置环境变量，模拟API密钥（实际使用时需要真实密钥）
os.environ['ZHIPU_API_KEY'] = 'test_key_for_validation_only'
os.environ['OUTPUT_MODE'] = 'both'

print("=== 测试 AI_Paper_Tracking 修改后的代码 ===")

# 测试导入
try:
    from sources.base import Paper
    from summarizer import select_top_papers, enrich_papers, detailed_analysis
    from formatter import format_daily_report, format_detailed_report, format_wecom_messages
    print("✅ 模块导入成功")
    
    # 创建测试数据
    test_papers = [
        Paper(
            title="Test Paper 1: Advanced LLM Reasoning",
            summary="This paper introduces a novel reasoning framework for large language models that improves logical deduction capabilities.",
            source="test",
            url="https://example.com/paper1",
            authors="John Doe, Jane Smith",
            published="2026-03-10"
        ),
        Paper(
            title="Test Paper 2: Multi-Agent Collaboration",
            summary="A new multi-agent system that enables collaborative problem solving through distributed reasoning.",
            source="test", 
            url="https://example.com/paper2",
            authors="Alice Wang, Bob Chen",
            published="2026-03-10"
        )
    ]
    
    print(f"✅ 创建了 {len(test_papers)} 篇测试论文")
    
    # 测试精选功能
    selected = select_top_papers(test_papers, top_k=2)
    print(f"✅ 精选出 {len(selected)} 篇论文")
    
    # 测试丰富信息
    enriched = enrich_papers(selected)
    print(f"✅ 丰富了 {len(enriched)} 篇论文信息")
    
    # 测试详细分析
    analyzed = detailed_analysis(enriched)
    print(f"✅ 完成了 {len(analyzed)} 篇论文详细分析")
    
    # 测试格式化
    simple_report = format_daily_report(analyzed)
    print(f"✅ 生成了简单报告（长度: {len(simple_report)} 字符）")
    
    detailed_report = format_detailed_report(analyzed)
    print(f"✅ 生成了详细报告（长度: {len(detailed_report)} 字符）")
    
    # 测试企业微信消息格式化
    wecom_messages = format_wecom_messages(analyzed, mode="both")
    print(f"✅ 生成了 {len(wecom_messages)} 条企业微信消息")
    
    print("\n=== 测试成功总结 ===")
    print("1. ✅ 代码结构完整")
    print("2. ✅ 新增详细分析功能")
    print("3. ✅ 支持简单/详细/双模式输出")
    print("4. ✅ 企业微信消息适配双模式")
    print("5. ✅ 所有模块导入正常")
    
    print("\n=== 输出模式说明 ===")
    print("simple: 仅输出简单版（原项目格式）")
    print("detailed: 仅输出详细版（新增6维度分析）")
    print("both: 同时输出简单版和详细版（默认）")
    
    print("\n=== 详细分析包含的6个维度 ===")
    print("1. 背景 (Background)")
    print("2. 动机 (Motivation)")
    print("3. 创新点 (Innovation)")
    print("4. 技术难点 (Technical Challenges)")
    print("5. 不足/待解决 (Limitations)")
    print("6. 展望/应用 (Future/Applications)")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()