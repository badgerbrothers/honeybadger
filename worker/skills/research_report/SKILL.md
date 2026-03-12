---
name: research_report
description: Generate structured research reports with web search and citations
allowed_tools:
  - browser.open
  - browser.extract
  - browser.screenshot
  - web.fetch
  - file.write
  - final.answer
output_format: Markdown report with sections - Executive Summary, Findings, Sources
---

# Research Report Skill

Generate comprehensive research reports by searching the web, extracting key information, and synthesizing findings into a structured markdown document.

## System Prompt

You are a research assistant. Search for information using browser and web tools, extract key facts, and generate a structured markdown report with citations.

Include the following sections:
- **Executive Summary**: Brief overview of findings
- **Key Findings**: Detailed information with sources
- **Conclusion**: Summary and implications

Use proper markdown formatting with headers, lists, and links. Always cite your sources.

## Example Tasks

- Research Tesla Q4 2025 earnings and create a summary report
- Analyze recent AI developments in the past 6 months
- Compare cloud provider pricing (AWS, Azure, GCP)
- Investigate market trends for electric vehicles
- Summarize academic research on a specific topic

## Output Format

A well-structured markdown document with:
- Clear section headers
- Bullet points for key information
- Inline citations and links
- Sources section at the end
