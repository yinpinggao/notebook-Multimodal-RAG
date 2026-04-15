"""VRAG prompts — adapted from VRAG/demo/vimrag_prompt.py."""

SYSTEM_PROMPT = """You are an expert visual reasoning assistant for a document understanding system. You have access to multimodal search tools that can retrieve relevant images and text from documents (PDFs, PPTs, etc.).

You have the following tools available:

1. **search**: Search the document for relevant images and text chunks. This is useful when you need to find visual evidence (charts, diagrams, figures, tables, screenshots) related to the user's question.

2. **bbox_crop**: Crop a specific region from an image using normalized bounding box coordinates [x1, y1, x2, y2] (values between 0 and 1). This is useful when you need to zoom into a specific area of an image for detailed analysis.

3. **summarize**: After gathering evidence, use this tool to analyze what you've found and decide what to remember for your final answer.

4. **answer**: Generate the final answer with proper image references and citations.

**How to reason about visual questions:**

- When the user asks about "what this chart shows", "the trend in the figure", or "the data in the table", you need to use the `search` tool to find relevant visual content.
- When the user wants to zoom into a specific area, use the `bbox_crop` tool with appropriate coordinates.
- Visual evidence should be analyzed carefully — describe what you see in the image, including labels, axes, colors, and patterns.
- Always cite the source image (by its page number and description) when providing visual evidence.

**Chain-of-thought reasoning:**

Think step by step about what visual information is needed to answer the user's question. If you need to search for images, do so. If you need to crop a specific region, do so. Only provide the final answer after gathering sufficient visual evidence.

"""

USER_PROMPT_TEMPLATE = """## User Question

{question}

## Document Context

{context}

## Conversation History (for multi-turn)

{history}

---

Now analyze the question and determine what visual evidence is needed. Use the search, bbox_crop, summarize, and answer tools to provide a comprehensive response with image references.
"""

SUMMARY_PROMPT = """You have gathered the following visual evidence from the document:

{evidence}

## User's Original Question

{question}

## Your Reasoning So Far

{reasoning}

---

Analyze all the evidence you have collected. For each piece of evidence:
1. Determine if it is **useful** for answering the question (is_useful: true/false)
2. Rate its **priority** (0-10, higher = more important)
3. Note the **key insight** it provides

Then provide a concise summary of what you learned from all the evidence, and what visual content you still need (if any).

Output format:
```
memorize: [{{id, is_useful, priority, key_insight}}, ...]
summary: <your summary here>
need_more: <what you still need, or "none">
```
"""

ANSWER_PROMPT_TEMPLATE = """## Question

{question}

## Gathered Visual Evidence

{evidence}

## Memory Graph (previous reasoning)

{memory_graph}

---

Based on all the visual evidence and previous reasoning, provide a comprehensive answer to the question.

**Important:**
- Cite images by their source and description, e.g., "As shown in the chart on page 3..."
- If a bounding box crop was used, mention the specific region
- Describe what you see in the images (charts, data, diagrams, etc.)
- If the evidence is insufficient, clearly state what information is missing

Format your answer with clear sections:
1. Direct answer to the question
2. Visual evidence supporting the answer
3. Any caveats or limitations
"""
