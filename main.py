import os
import feedparser
from datetime import datetime, timedelta
import openai
import requests

FEEDS = {
    "PhilArchive_Mind": "https://philarchive.org/recent/mind",
    "bioRxiv_Neuro": "https://connect.biorxiv.org/biorxiv_xml.php?subject=neuroscience",
    "TiCS": "https://www.cell.com/trends/cognitive-sciences/rss.xml"
}

def collect_feeds(days=7):
    cutoff = datetime.now() - timedelta(days=days)
    items = []
    for source, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            items.append({
                "source": source,
                "title": entry.title,
                "summary": entry.get("summary", ""),
                "link": entry.link
            })
    return items

def generate_report(papers):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"다음 논문 후보군 중 가장 학술적 가치가 높은 5편을 선별해 Executive Summary를 작성하세요:\n\n{papers[:20]}"
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "인지과학/인지철학 전문 학술 분석가입니다. 주간 브리핑 양식으로 정결하게 요약하세요."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def append_to_notion(content):
    notion_key = os.getenv("NOTION_API_KEY")
    page_id = os.getenv("NOTION_PAGE_ID")
    if not notion_key or not page_id:
        print("Notion 환경변수 미설정: 콘솔 출력으로 대체")
        print(content)
        return

    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {notion_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 2000자 초과 방지를 위한 청크 분할 전송
    chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        } for chunk in chunks
    ]
    requests.patch(url, headers=headers, json={"children": children})

if __name__ == "__main__":
    raw_papers = collect_feeds()
    report = generate_report(raw_papers)
    append_to_notion(report)
