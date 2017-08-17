import asyncio


class Message(object):

    def __init__(self, payload=None):
        self.payload = payload

    def __repr__(self):
        return 'Message (Payload: {0})'.format(self.payload)


class QueryMessage(Message):
    '''Special type of message that expects a response'''
    def __init__(self, payload=None):
        super().__init__(payload)
        self.result = None
        '''Future, set in ``AbstractActor.ask`` if not set by user'''
    def __repr__(self):
        return 'QueryMessage (Payload: {0})'.format(self.payload)

class StopMessage(Message):
    '''Special type of message that tells actors to quit processing 
    their inbox
    '''
    def __repr__(self):
        return 'StopMessage (Payload: {0})'.format(self.payload)
