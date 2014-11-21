import json

import mock

from gratipay.exceptions import EmailAlreadyTaken
from gratipay.models.participant import Participant
from gratipay.testing import Harness


class TestEmail(Harness):

    def setUp(self):
        self.alice = self.make_participant('alice', claimed_time='now')

    @mock.patch.object(Participant, 'send_email')
    def hit_email_spt(self, action, address, send_email, user='alice', should_fail=False):
        P = self.client.PxST if should_fail else self.client.POST
        data = {'action': action, 'address': address}
        return P('/alice/email.json', data, auth_as=user)

    def verify_email(self, email, nonce, username='alice', should_fail=False):
        url = '/%s/verify-email.html?email=%s&nonce=%s' % (username, email, nonce)
        G = self.client.GxT if should_fail else self.client.GET
        return G(url)

    def verify_and_change_email(self, old_email, new_email, username='alice'):
        self.hit_email_spt('add-email', old_email)
        nonce = Participant.from_username(username).get_email(old_email).nonce
        self.verify_email(old_email, nonce)
        self.hit_email_spt('add-email', new_email)

    def test_participant_can_add_email(self):
        response = self.hit_email_spt('add-email', 'alice@gratipay.com')
        actual = json.loads(response.body)
        assert actual == 1

    def test_post_anon_returns_403(self):
        response = self.hit_email_spt('add-email', 'anon@gratipay.com', user=None, should_fail=True)
        assert response.code == 403

    def test_post_with_no_at_symbol_is_400(self):
        response = self.hit_email_spt('add-email', 'gratipay.com', should_fail=True)
        assert response.code == 400

    def test_post_with_no_period_symbol_is_400(self):
        response = self.hit_email_spt('add-email', 'test@gratipay', should_fail=True)
        assert response.code == 400

    def test_verify_email_without_adding_email(self):
        response = self.verify_email('', 'sample-nonce')
        assert 'Failed to verify' in response.body

    def test_verify_email_wrong_nonce(self):
        self.hit_email_spt('add-email', 'alice@example.com')
        nonce = 'fake-nonce'
        r = self.alice.verify_email('alice@gratipay.com', nonce)
        assert r == 2
        self.verify_email('alice@example.com', nonce)
        expected = None
        actual = Participant.from_username('alice').email_address
        assert expected == actual

    def test_verify_email_expired_nonce(self):
        address = 'alice@example.com'
        self.hit_email_spt('add-email', address)
        self.db.run("""
            UPDATE emails
               SET ctime = (now() - INTERVAL '25 hours')
             WHERE participant = 'alice'
        """)
        nonce = self.alice.get_email(address).nonce
        r = self.alice.verify_email(address, nonce)
        assert r == 1
        actual = Participant.from_username('alice').email_address
        assert actual == None

    def test_verify_email(self):
        self.hit_email_spt('add-email', 'alice@example.com')
        nonce = self.alice.get_email('alice@example.com').nonce
        self.verify_email('alice@example.com', nonce)
        expected = 'alice@example.com'
        actual = Participant.from_username('alice').email_address
        assert expected == actual

    def test_verified_email_is_not_changed_after_update(self):
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        expected = 'alice@example.com'
        actual = Participant.from_username('alice').email_address
        assert expected == actual

    def test_get_emails(self):
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        emails = self.alice.get_emails()
        assert len(emails) == 2

    def test_verify_email_after_update(self):
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        nonce = self.alice.get_email('alice@example.net').nonce
        self.verify_email('alice@example.net', nonce)
        expected = 'alice@example.net'
        actual = Participant.from_username('alice').email_address
        assert expected == actual

    def test_nonce_is_reused_when_resending_email(self):
        self.hit_email_spt('add-email', 'alice@example.com')
        nonce1 = self.alice.get_email('alice@example.com').nonce
        self.hit_email_spt('resend', 'alice@example.com')
        nonce2 = self.alice.get_email('alice@example.com').nonce
        assert nonce1 == nonce2

    @mock.patch.object(Participant, 'send_email')
    def test_cannot_update_email_to_already_verified(self, send_email):
        bob = self.make_participant('bob', claimed_time='now')
        self.alice.add_email('alice@gratipay.com')
        nonce = self.alice.get_email('alice@gratipay.com').nonce
        self.alice.verify_email('alice@gratipay.com', nonce)
        with self.assertRaises(EmailAlreadyTaken):
            bob.update_email('alice@gratipay.com')
        assert self.alice.email_address == 'alice@gratipay.com'

    @mock.patch.object(Participant, 'send_email')
    def test_can_verify_email(self, send_email):
        email = 'alice@gratipay.com'
        self.alice.add_email(email)
        nonce = self.alice.get_email(email).nonce
        r = self.alice.verify_email(email, nonce)
        assert r == 0
        actual = Participant.from_username('alice').email_address
        expected = 'alice@gratipay.com'
        assert actual == expected

    def test_account_page_shows_emails(self):
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        body = self.client.GET("/alice/account/", auth_as="alice").body
        assert 'alice@example.com' in body
        assert 'alice@example.net' in body