import asyncio
import platform
from typing import Any

import fire

from metagpt.actions import Action, UserRequirement
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.team import Team


class Describe(Action):
    PROMPT_TEMPLATE: str = """
    ## BACKGROUND
    Suppose you are {name}, and you are playing the game "You describe me and I guess". 
    Human users will provide a name for an object, and you need to describe the object in detail to guide your AI partners whose name is {partners_name}, to guess its name. 
    Remember, you cannot directly mention the name of this object.
    ## OBJECT NAME PROVIDED BY HUMAN USER:
    {obejct_name}
    ## CHAT HISTORY
    {context}
    ## YOUR TURN
    Now it's your turn. You need to describe the object provided by human user in detail and guide your AI partner {partners_name} to guess its name.
    If you receive guesses from {partners_name}, please answer if they are correct. 
    If it is correct, please congratulate {partners_name} and stop the game.
    If it is not correct, please further optimize your description to help {partners_name} guess the name of this object.
    If {partners_name} asks you a question, optimize your description based on his question, but cannot directly state the name of the object.
    """
    name: str = "Describe"

    async def run(self, obejct_name, context, name, partners_name):
        prompt = self.PROMPT_TEMPLATE.format(obejct_name=obejct_name, context=context, name=name,
                                             partners_name=partners_name)
        # logger.info(prompt)
        rsp = await self._aask(prompt)
        return rsp


class Guess(Action):
    PROMPT_TEMPLATE: str = """
    ## BACKGROUND
    Suppose you are {name}, and you are playing the game "You describe me and I guess". You need to guess the name of an object based on the description of your AI partner whose name is {partners_name}. 
    If you can't guess, you can continue to ask AI partners {partners_name} questions, but you can't directly ask the name of the object.
    ## CHAT HISTORY
    Previous rounds:
    {context}
    ## YOUR TURN
    Now it's your turn. Please guess the name of the object based on the description of your {partners_name}. 
    If you can't guess, you can continue to ask {partners_name} questions, but you can't directly ask for the name of the object.
    """
    name: str = "Guess"

    async def run(self, context, name, partners_name):
        prompt = self.PROMPT_TEMPLATE.format(context=context, name=name, partners_name=partners_name)
        rsp = await self._aask(prompt)
        return rsp


class Descriptor(Role):
    name: str = ""
    profile: str = ""
    partners_name: str = ""
    obejct_name: str = ""

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.set_actions([Describe])
        self._watch([UserRequirement, Guess])

    async def _observe(self) -> int:
        await super()._observe()
        self.rc.news = [msg for msg in self.rc.news if msg.send_to == {self.name}]
        return len(self.rc.news)

    async def _act(self, obejct_name=None) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo

        memories = self.get_memories()
        context = "\n".join(f"{msg.sent_from}: {msg.content}" for msg in memories)

        rsp = await todo.run(obejct_name=self.obejct_name, context=context, name=self.name,
                             partners_name=self.partners_name)

        msg = Message(
            content=rsp,
            role=self.profile,
            cause_by=type(todo),
            sent_from=self.name,
            send_to=self.partners_name,
        )
        self.rc.memory.add(msg)

        return msg


class Guesser(Role):
    name: str = ""
    profile: str = ""
    partners_name: str = ""

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.set_actions([Guess])
        self._watch([Describe])

    async def _observe(self) -> int:
        await super()._observe()
        self.rc.news = [msg for msg in self.rc.news if msg.send_to == {self.name}]
        return len(self.rc.news)

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo

        memories = self.get_memories()
        context = "\n".join(f"{msg.sent_from}: {msg.content}" for msg in memories)

        rsp = await todo.run(context=context, name=self.name, partners_name=self.partners_name)

        msg = Message(
            content=rsp,
            role=self.profile,
            cause_by=type(todo),
            sent_from=self.name,
            send_to=self.partners_name,
        )
        self.rc.memory.add(msg)

        return msg


async def describe_and_guess(idea: str, investment: float = 3.0, n_round: int = 5):
    descriptor = Descriptor(name="Descriptor", profile="Descriptor", partners_name="Guesser",obejct_name=idea)
    guesser = Guesser(name="Guesser", profile="Guesser", partners_name="Descriptor")
    team = Team()
    team.hire([descriptor, guesser])
    team.invest(investment)
    team.run_project(idea, send_to="Descriptor")
    await team.run(n_round=n_round)


def main(idea: str = "Banana", investment: float = 3.0, n_round: int = 3):
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(describe_and_guess(idea, investment, n_round))


if __name__ == "__main__":
    fire.Fire(main)
