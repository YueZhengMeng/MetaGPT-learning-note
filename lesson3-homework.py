import asyncio

from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message


class PrintAction(Action):
    name: str = "PrintAction"

    async def run(self, action_ID: str):
        logger.info(f"Action {action_ID} is running...")
        return str(int(action_ID) + 1)


class PrintRole(Role):
    name: str = "Jod"
    profile: str = "PrintRole"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # MetaGPT版本0.8.1请使用set_actions方法为Role加入Action
        # self._init_actions([SimpleWriteCode, SimpleRunCode])
        logger.info("add action 1,2,3")
        self.set_actions([PrintAction, PrintAction, PrintAction])

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        # By choosing the Action by order under the hood
        # todo will be first SimpleWriteCode() then SimpleRunCode()
        todo = self.rc.todo
        # 只需要获取最近的一条记忆，也就是用户下达的需求，将它传递给action即可
        msg = self.get_memories(k=1)[0]  # find the most recent messagesA

        result = await todo.run(msg.content)

        if result == '4':
            logger.info("add action 4,5,6")
            self.set_actions([PrintAction, PrintAction, PrintAction])
            self.rc.todo = None

        msg = Message(content=result, role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg

    async def _think(self) -> None:
        """Determine the next action to be taken by the role."""
        if self.rc.todo is None:
            self._set_state(0)
            return

        if self.rc.state + 1 < len(self.states):
            self._set_state(self.rc.state + 1)
        else:
            self.rc.todo = None

    async def _react(self) -> Message:
        """Execute the assistant's think and actions.

        Returns:
            A message containing the final result of the assistant's actions.
        """
        while True:
            await self._think()
            if self.rc.todo is None:
                break
            msg = await self._act()
        return msg


async def main():
    msg = "1"
    role = PrintRole()
    await role.run(msg)


asyncio.run(main())
