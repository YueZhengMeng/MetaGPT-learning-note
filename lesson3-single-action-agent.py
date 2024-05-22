import re
import asyncio
from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger


class SimpleWriteCode(Action):
    PROMPT_TEMPLATE: str = """
    Write a python function that can {instruction} and provide two runnable test cases.
    Return ```python your_code_here ``` with NO other texts,
    your code:
    """

    name: str = "SimpleWriteCode"

    async def run(self, instruction: str):
        # 提示词模板
        prompt = self.PROMPT_TEMPLATE.format(instruction=instruction)
        # 获取 LLM 的回复
        rsp = await self._aask(prompt)
        code_text = SimpleWriteCode.parse_code(rsp)
        return code_text

    @staticmethod
    def parse_code(rsp):
        # 查找以 ```python 开头且以```结尾的代码块，并提取其中的代码内容
        pattern = r'```python(.*)```'
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        return code_text


class SimpleCoder(Role):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 为 Role 配备了我们之前写好的动作 SimpleWriteCode
        # 我们定义的行动SimpleWriteCode就会被加入到代办self.rc.todo中
        # MetaGPT版本0.8.1请使用set_actions方法为Role加入Action
        # self._init_actions([SimpleWriteCode])
        self.set_actions([SimpleWriteCode])

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo  # todo will be SimpleWriteCode()
        # 只需要获取最近的一条记忆，也就是用户下达的需求，将它传递给action即可
        msg = self.get_memories(k=1)[0]  # find the most recent messages

        code_text = await todo.run(msg.content)
        msg = Message(content=code_text, role=self.profile, cause_by=type(todo))

        return msg


async def main():
    msg = "write a function that calculates the sum of a list"
    role = SimpleCoder()
    logger.info(msg)
    # 运行SimpleCoder角色
    result = await role.run(msg)
    logger.info(result)


asyncio.run(main())
