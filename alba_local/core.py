"""Application adapter. The caller must authenticate user IDs before invoking owner-scoped methods."""
import asyncio
from pathlib import Path
from aiohttp import ClientSession
from .config import Settings
from .store import Store
from .security import Keys,secret_file
from .engine import Engine
from .service import Service,Incoming
from .backups import Backups
from .telegram_bot import Telegram
from .maintenance_tasks import memory_cycle,periodic_memory

class AlbaLocal:
    def __init__(self,root,admins=(),allowed=(),**settings):self.settings=Settings(root=Path(root).resolve(),admins=tuple(admins),allowed=tuple(allowed),**settings)
    async def __aenter__(self):
        self.session=ClientSession(trust_env=False);self.store=Store(self.settings.data/'alba.sqlite3');self.keys=Keys(self.store,secret_file(self.settings.data/'auth.key'));self.engine=Engine(self.store,self.settings,self.session);self.service=Service(self.store,self.settings,self.keys,self.engine,Backups(self.store,self.settings));return self
    async def __aexit__(self,*args):
        tasks=[entry['task'] for entry in self.service.active_responses.values()]
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        await self.session.close();self.store.close()
    async def reply(self,user_id,text,name='Utente'):
        result=await self.service.handle(Incoming(user_id,name,user_id,'private',text,transport='web'));return result.text
    def authorize(self,user_id,actor):
        if not self.service.is_admin(actor):raise PermissionError('Serve un amministratore verificato dall’applicazione ospite.')
        self.store.authorize(user_id,self.settings.max_users);self.store.execute('DELETE FROM access_blocks WHERE user_id=?',(user_id,));self.store.audit(actor,'adapter_authorize',user_id)
    def web_key(self,user_id):return self.keys.issue(user_id,user_id,'web',self.settings.key_ttl)
    def verify_web_key(self,token,remember=True):
        cookie,csrf=self.keys.session(token,remember);return {'session':cookie,'csrf':csrf,'user_id':self.keys.identify(cookie)['user_id']}
    def identify_session(self,token):return self.keys.identify(token)
    async def consolidate(self):return await memory_cycle(self.store)
    async def run_telegram(self):
        if not self.settings.bot_token:raise ValueError('Configura bot_token ottenuto da BotFather.')
        telegram=Telegram(self.service,self.session,self.settings.bot_token)
        async def backups():
            while True:
                self.service.backups.scheduled();await asyncio.sleep(3600)
        tasks=[asyncio.create_task(periodic_memory(self.store,self.service)),asyncio.create_task(self.service.performance.run()),asyncio.create_task(backups())]
        try:await telegram.run()
        finally:
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
