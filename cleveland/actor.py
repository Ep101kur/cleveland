import asyncio
import warnings

from .message import StopMessage, QueryMessage


class HandlerNotFoundError(KeyError): 
    pass


class ActorStopError(Exception):
    """Raise when a Actor receive a message after he received a StopMessage"""


class AbstractActor(object):

    def __init__(self, *args, **kwargs):
        self._loop = kwargs['loop'] if 'loop' in kwargs \
            else asyncio.get_event_loop()
        self._is_running = False
        self._run_complete = asyncio.Future(loop=self._loop)

    def start(self):
        self._is_running = True
        self._loop.create_task(self._run())


    async def stop(self):
        self._is_running = False
        await self._stop()
        await self._run_complete
        return True

    def _start(self): 
        '''Custom startup logic, override in subclasses'''


    async def _stop(self):
        '''Custom shutdown logic, override in subclasses'''


    async def _run(self):
        '''The actor's main work loop'''
      
        while self._is_running:
            await self._task()

        # Signal that the loop has finished.
        self._run_complete.set_result(True)


    async def _task(self):
        raise NotImplementedError('Subclasses of AbstractActor must implement '
                                  '_task()')

    @staticmethod
    async def tell(target, message):
        try:
            await target._receive(message)
        except AttributeError as ex:
            raise TypeError('Target does not have a _receive method. Is it an actor?') from ex


    async def ask(self, target, message):
        assert isinstance(message, QueryMessage)
        if not message.result:
            message.result = asyncio.Future(loop=self._loop)
          
        await self.tell(target, message)
        return await message.result


class BaseActor(AbstractActor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_inbox_size = kwargs.get('max_inbox_size', 0)
        self._inbox = asyncio.Queue(maxsize=self._max_inbox_size,
                                    loop=self._loop)
        self._handlers = {}

        # Create handler for the 'poison pill' message
        self.register_handler(StopMessage, self._stop_message_handler)

    def register_handler(self, message_cls, func):
        self._handlers[message_cls] = func


    async def _task(self):
        message = await self._inbox.get()
        try:
            handler = self._handlers[type(message)]
            is_query = isinstance(message, QueryMessage)
            try:
                response = await handler(message)
            except Exception as ex:
                if is_query:
                    message.result.set_exception(ex)
                else:
                    warnings.warn('Unhandled exception from handler of '
                                  '{0}'.format(type(message)))
            else:
                if is_query:
                    message.result.set_result(response)
        except KeyError as ex:
            raise HandlerNotFoundError(type(message)) from ex


    async def _stop(self):
        await self._receive(StopMessage())

    async def _receive(self, message):
        # TODO: Find a more pythonic way to check if Actor is alive
        if self._is_running or isinstance(message, StopMessage):
            await self._inbox.put(message)
        else:
            raise ActorStopError("Actor has already received a StopMessage")

    async def _stop_message_handler(self, message):
        '''The stop message is only to ensure that the queue has at least one
        item in it so the call to _inbox.get() doesn't block. We don't actually
        have to do anything with it.
        '''
        if self._is_running:
            self._is_running = False


