"""Prompts for Vision Language Model (VLM) functionality."""

# Prompt for extracting text from images using VLM
VLM_IMAGE_EXTRACTION_PROMPT = (
    "请仔细阅读这张图片中的所有文字内容，包括图表、表格、标题、正文等，并将关键文字内容简洁提取出来。"
    "如包含表格，请以结构化方式简要描述表格内容。"
    "请保持输出精简，避免冗余描述，只提取必要信息。"
)

# Enhanced prompt for generating structured page summaries
VLM_PAGE_SUMMARY_PROMPT = """请分析这张PDF页面图片（第{page_num}页），生成结构化的页面摘要。

【已提取的文字参考】
{existing_text}

【分析要求】
1. 识别页面的主要内容类型（如：正文、表格、图表、标题页等）
2. 提取页面的核心信息和关键数据
3. 如有表格，提取表格的标题和关键数据
4. 如有图表，描述图表展示的主要信息
5. 识别页面中提到的公司名称、时间、数字等关键实体

【输出格式】
- 页面类型：[正文/表格/图表/混合]
- 核心内容：[简要描述页面的主要内容，50-200字]
- 关键数据：[列出页面中的重要数字、百分比、日期等]
- 关键实体：[提及的公司、产品、人物等]

请保持输出简洁精准，避免冗余。"""

# Prompt for analyzing tables and charts specifically
VLM_TABLE_CHART_PROMPT = """请详细分析这张图片中的表格或图表内容。

【分析要求】
1. 识别表格/图表的标题
2. 提取所有列名和行名
3. 提取关键数据点和数值
4. 总结数据的主要趋势或结论

【输出格式】
表格/图表标题：
数据内容：
- [行/项目名]: [对应数值或描述]
主要结论：[一句话总结]

请保持输出结构化，便于检索。"""
