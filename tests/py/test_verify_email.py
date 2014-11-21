import mock

from gratipay.models.participant import Participant
from gratipay.testing import Harness


class TestForVerifyEmail(Harness):

    @mock.patch.object(Participant, 'send_email')
    def change_email_address(self, address, username, send_email):
        url = "/%s/email.json" % username
        return self.client.POST(url, {'email': address}, auth_as=username)

    def verify_email(self, username, email, nonce, should_fail=False):
        url = '/%s/verify-email.html?email=%s&nonce=%s' % (username, email, nonce)
        G = self.client.GxT if should_fail else self.client.GET
        return G(url)

    def verify_and_change_email(self, username, old_email, new_email):
        self.change_email_address(old_email, username)
        nonce = Participant.from_username(username).get_email_nonce_and_ctime(old_email)[0]
        self.verify_email(username, old_email, nonce)
        self.change_email_address(new_email, username)

    def test_verify_email_without_adding_email(self):
        participant = self.make_participant('alice')
        response = self.verify_email(participant.username, '', 'sample-nonce', should_fail=True)
        assert response.code == 404

    def test_verify_email_wrong_nonce(self):
        participant = self.make_participant('alice', claimed_time="now")
        self.change_email_address('alice@gmail.com', participant.username)
        self.verify_email(participant.username, 'alice@gmail.com', 'sample-nonce')
        expected = None
        actual = Participant.from_username(participant.username).email_address
        assert expected == actual

    def test_verify_email(self):
        participant = self.make_participant('alice', claimed_time="now")
        self.change_email_address('alice@gmail.com', participant.username)
        nonce = Participant.from_username(participant.username)
        nonce = Participant.from_username('alice').get_email_nonce_and_ctime('alice@gmail.com')[0]
        self.verify_email(participant.username, 'alice@gmail.com', nonce)
        expected = 'alice@gmail.com'
        actual = Participant.from_username(participant.username).email_address
        assert expected == actual

    def test_verified_email_is_not_changed_after_update(self):
        participant = self.make_participant('alice', claimed_time="now")
        self.verify_and_change_email('alice', 'alice@gmail.com', 'alice@yahoo.com')
        expected = 'alice@gmail.com'
        actual = Participant.from_username(participant.username).email_address
        assert expected == actual

    def test_unverified_email_is_set_after_update(self):
        participant = self.make_participant('alice', claimed_time="now")
        self.verify_and_change_email('alice', 'alice@gmail.com', 'alice@yahoo.com')
        expected = 'alice@yahoo.com'
        actual = Participant.from_username(participant.username).get_unverified_email()
        assert expected == actual

    def test_verify_email_after_update(self):
        participant = self.make_participant('alice', claimed_time="now")
        self.verify_and_change_email('alice', 'alice@gmail.com', 'alice@yahoo.com')
        nonce = Participant.from_username('alice').get_email_nonce_and_ctime('alice@yahoo.com')[0]
        self.verify_email(participant.username, 'alice@yahoo.com', nonce)
        expected = 'alice@yahoo.com'
        actual = Participant.from_username(participant.username).email_address
        assert expected == actual

    def test_nonce_is_regenerated_on_update(self):
        participant = self.make_participant('alice', claimed_time="now")
        self.change_email_address('alice@gmail.com', participant.username)
        nonce1 = Participant.from_username('alice').get_email_nonce_and_ctime('alice@gmail.com')[0]
        self.change_email_address('alice@gmail.com', participant.username)
        nonce2 = Participant.from_username('alice').get_email_nonce_and_ctime('alice@gmail.com')[0]
        assert nonce1 != nonce2

    def test_latest_nonce_is_considered(self):
        participant = self.make_participant('alice', claimed_time="now")
        self.change_email_address('alice@gmail.com', participant.username)
        nonce1 = Participant.from_username('alice').get_email_nonce_and_ctime('alice@gmail.com')[0]
        self.change_email_address('alice@gmail.com', participant.username)
        nonce2 = Participant.from_username('alice').get_email_nonce_and_ctime('alice@gmail.com')[0]

        self.verify_email(participant.username, 'alice@gmail.com', nonce1)
        expected = None
        actual = Participant.from_username(participant.username).email_address
        assert expected == actual

        self.verify_email(participant.username, 'alice@gmail.com', nonce2)
        expected = 'alice@gmail.com'
        actual = Participant.from_username(participant.username).email_address
        assert expected == actual
