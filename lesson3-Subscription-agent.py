import asyncio
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from metagpt.actions.action import Action
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message

# Actions 的实现
TRENDING_ANALYSIS_PROMPT = """# Requirements
You are a GitHub Trending Analyst, aiming to provide users with insightful and personalized recommendations based on the latest
GitHub Trends. Based on the context, fill in the following missing information, generate engaging and informative titles, 
ensuring users discover repositories aligned with their interests.

# The title about Today's GitHub Trending
## Today's Trends: Uncover the Hottest GitHub Projects Today! Explore the trending programming languages and discover key domains capturing developers' attention. From ** to **, witness the top projects like never before.
## The Trends Categories: Dive into Today's GitHub Trending Domains! Explore featured projects in domains such as ** and **. Get a quick overview of each project, including programming languages, stars, and more.
## Highlights of the List: Spotlight noteworthy projects on GitHub Trending, including new tools, innovative projects, and rapidly gaining popularity, focusing on delivering distinctive and attention-grabbing content for users.
---
# Format Example

```
# [Title]

## Today's Trends
Today, ** and ** continue to dominate as the most popular programming languages. Key areas of interest include **, ** and **.
The top popular projects are Project1 and Project2.

## The Trends Categories
1. Generative AI
    - [Project1](https://github/xx/project1): [detail of the project, such as star total and today, language, ...]
    - [Project2](https://github/xx/project2): ...
...

## Highlights of the List
1. [Project1](https://github/xx/project1): [provide specific reasons why this project is recommended].
...
```

---
# Github Trending
{trending}
"""


async def fetch_html(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy="http://127.0.0.1:7890") as response:
            return await response.text()


async def parse_github_trending(html):
    soup = BeautifulSoup(html, 'html.parser')

    repositories = []

    for article in soup.select('article.Box-row'):
        repo_info = {}

        repo_info['name'] = article.select_one('h2 a').text.strip()
        repo_info['url'] = article.select_one('h2 a')['href'].strip()

        # Description
        description_element = article.select_one('p')
        repo_info['description'] = description_element.text.strip() if description_element else None

        # Language
        language_element = article.select_one('span[itemprop="programmingLanguage"]')
        repo_info['language'] = language_element.text.strip() if language_element else None

        # Stars and Forks
        stars_element = article.select('a.Link--muted')[0]
        forks_element = article.select('a.Link--muted')[1]
        repo_info['stars'] = stars_element.text.strip()
        repo_info['forks'] = forks_element.text.strip()

        # Today's Stars
        today_stars_element = article.select_one('span.d-inline-block.float-sm-right')
        repo_info['today_stars'] = today_stars_element.text.strip() if today_stars_element else None

        repositories.append(repo_info)

    return repositories


class CrawlOSSTrending(Action):
    async def run(self, url: str = "https://github.com/trending"):
        global repositories
        return repositories


class AnalysisOSSTrending(Action):
    async def run(self, trending: Any):
        return await self._aask(TRENDING_ANALYSIS_PROMPT.format(trending=trending))


# Role实现
class OssWatcher(Role):
    def __init__(
            self,
            name="Codey",
            profile="OssWatcher",
            goal="Generate an insightful GitHub Trending analysis report.",
            constraints="Only analyze based on the provided GitHub Trending data.",
    ):
        super().__init__(name=name, profile=profile, goal=goal, constraints=constraints)
        self.set_actions([CrawlOSSTrending, AnalysisOSSTrending])
        self._set_react_mode(react_mode="by_order")

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        # By choosing the Action by order under the hood
        # todo will be first SimpleWriteCode() then SimpleRunCode()
        todo = self.rc.todo

        msg = self.get_memories(k=1)[0]  # find the most k recent messages
        result = await todo.run(msg.content)

        msg = Message(content=str(result), role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg


async def main():
    global repositories
    url: str = "https://github.com/trending"
    html = await fetch_html(url)
    repositories = await parse_github_trending(html)

    msg = "Generate an insightful GitHub Trending analysis report."
    logger.info(msg)
    role = OssWatcher()
    result = await role.run(msg)
    logger.info(result)


asyncio.run(main())
