import unittest
from cleveland.actor import BaseActor, ActorStopError
from cleveland.message import Message, QueryMessage, StopMessage
import asyncio
import os


def async_test(fun):
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        coro = asyncio.wait_for(fun(*args, **kwargs), 3)
        loop.run_until_complete(coro)
    return wrapper


class TestActor(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @async_test
    async def test_start_stop_normal(self):
        t = (1, 2, 3)
        admin = BaseActor()
        actor = StatefulActor(t)
        admin.start()
        actor.start()
        await actor.stop()
        await admin.stop()

    @async_test
    async def test_start_init_state(self):
        t = (1, 2, 3)
        admin = BaseActor()
        actor = StatefulActor(t)
        admin.start()
        actor.start()
        self.assertEqual(actor._state, t)
        await actor.stop()
        await admin.stop()

    @async_test
    async def test_tell_changes_state(self):
        t = (1, 2, 3)
        t2 = (-1, -1, -1)
        admin = BaseActor()
        actor = StatefulActor(t)
        admin.start()
        actor.start()
        await admin.tell(actor, UpdateMessage(t2))
        while True:
            if actor._inbox.qsize() == 0:
                break
            await asyncio.sleep(0)
        self.assertEqual(actor._state, t2)
        await actor.stop()
        await admin.stop()

    @async_test
    async def test_ask(self):
        t = (1, 2, 3)
        t2 = (-1, -1, -1)
        admin = BaseActor()
        actor = StatefulActor(t)
        admin.start()
        actor.start()
        state = await admin.ask(actor, GetMessage())
        self.assertEqual(state, t)
        await admin.tell(actor, UpdateMessage(t2))
        state = await admin.ask(actor, GetMessage())
        self.assertEqual(state, t2)
        await actor.stop()
        await admin.stop()


    @async_test
    async def test_ask_two_task(self):
        t = (1,)
        t2 = (2,)
        admin = BaseActor()
        actor1 = StatefulActor(t)
        actor2 = StatefulActor(t2)
        admin.start()
        actor1.start()
        actor2.start()
        get_msg_1 = GetMessage()
        get_msg_2 = GetMessage()
        state1 = await admin.ask(actor1, get_msg_1)
        state2 = await admin.ask(actor2, get_msg_2)
        self.assertEqual(state1, t)
        self.assertEqual(state2, t2)
        await actor1.stop()
        await actor2.stop()
        await admin.stop()

    def test_start_stop_when_tell_StopMessage(self):
        pass

    @async_test
    async def test_talk_to_terminated_actor(self):
        admin = BaseActor()
        actor = StatefulActor(1)
        admin.start()
        actor.start()
        await actor.stop()
        with self.assertRaises(ActorStopError):
            await admin.tell(actor, UpdateMessage(2))
        await admin.stop()

    @async_test
    async def test_ask_a_terminated_actor(self):
        admin = BaseActor()
        actor = StatefulActor(1)
        admin.start()
        actor.start()
        await actor.stop()
        with self.assertRaises(ActorStopError):
            await admin.ask(actor, GetMessage())
        await admin.stop()

    @async_test
    async def test_ask_tell_msg(self):
        admin = BaseActor()
        actor = StatefulActor(1)
        admin.start()
        actor.start()
        with self.assertRaises(AssertionError):
            await admin.ask(actor, UpdateMessage(2))
        await actor.stop()
        await admin.stop()


    @async_test
    async def test_stop_a_stoped_actor(self):
        admin = BaseActor()
        admin.start()
        await admin.stop()
        await admin.stop()
        await admin._run_complete

    @async_test
    async def test_stop_with_StopMessage(self):
        admin = BaseActor()
        admin.start()
        await admin._receive(StopMessage())
        await admin._run_complete

class UpdateMessage(Message):
    def __repr__(self):
        return 'UpdateMessage (Payload: {0})'.format(self.payload)


class GetMessage(QueryMessage):
    pass


class StatefulActor(BaseActor):
    def __init__(self, state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_handler(UpdateMessage,
                              self._update_message_handler)
        self.register_handler(GetMessage,
                              self._get_message_handler)
        self._state = state

    async def _update_message_handler(self, message):
        self._state = message.payload

    async def _get_message_handler(self, message):
        return self._state

if __name__ == "__main__":
    os.environ["PYTHONASYNCIODEBUG"] = "1"
    unittest.main()
