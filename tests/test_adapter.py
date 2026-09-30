import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from alba_local import AlbaLocal
from alba_local.memory import build_context
from alba_local.store import Scope


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.alba = await AlbaLocal(self.directory.name, admins=[1], allowed=[2, 3]).__aenter__()
        self.alba.engine.generate = AsyncMock(return_value={
            'reply': 'Possiamo scegliere un prossimo passo concreto.',
            'used_memory_ids': [], 'personal_claims': [],
        })

    async def asyncTearDown(self):
        await self.alba.__aexit__()
        self.directory.cleanup()

    async def test_reply_persists_owner_and_sources(self):
        answer = await self.alba.reply(2, 'Mi chiamo Anna', 'Anna')
        self.assertIn('passo concreto', answer)
        self.assertEqual(self.alba.store.profile(2)[0]['content'], 'Mi chiamo Anna')
        self.assertFalse(self.alba.store.profile(3))

    async def test_group_and_other_user_context_exclude_private_data(self):
        await self.alba.reply(2, 'Mi chiamo SEGRETO_ANNA', 'Anna')
        for scope in [Scope('user', 3), Scope('group', -10)]:
            context = build_context(self.alba.store, scope, 'nome')
            self.assertNotIn('SEGRETO_ANNA', json.dumps(context))

    async def test_only_verified_admin_can_authorize(self):
        with self.assertRaises(PermissionError):
            self.alba.authorize(4, actor=2)
        self.alba.authorize(4, actor=1)
        self.assertTrue(self.alba.store.allowed(4))

    async def test_web_key_resolves_owner_and_is_single_use(self):
        token = self.alba.web_key(2)
        login = self.alba.verify_web_key(token)
        self.assertEqual(login['user_id'], 2)
        self.assertEqual(self.alba.identify_session(login['session'])['user_id'], 2)
        with self.assertRaises(PermissionError):
            self.alba.verify_web_key(token)

    async def test_export_key_cannot_access_another_owner(self):
        token = self.alba.keys.issue(2, 2, 'export')
        with self.assertRaises(PermissionError):
            self.alba.keys.consume(3, 2, token)

    async def test_memory_read_code_is_owner_issued_and_not_export(self):
        with self.assertRaises(PermissionError):
            self.alba.keys.issue(1, 2, 'memory_read')
        token = self.alba.keys.issue(2, 2, 'memory_read')
        with self.assertRaises(PermissionError):
            self.alba.keys.consume(1, 2, token, ('delegate',))
        self.alba.keys.consume(1, 2, token, ('memory_read',))
        with self.assertRaises(PermissionError):
            self.alba.keys.consume(1, 2, token, ('memory_read',))

    async def test_consolidation_keeps_original_messages(self):
        await self.alba.reply(2, 'Mi chiamo Anna', 'Anna')
        await self.alba.consolidate()
        messages = self.alba.store.recent(Scope('user', 2), 10)
        self.assertTrue(any(row['content'] == 'Mi chiamo Anna' for row in messages))
        self.assertTrue(Path(self.directory.name, 'data', 'alba.sqlite3').exists())


if __name__ == '__main__':
    unittest.main()
