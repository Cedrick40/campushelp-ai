import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import ChatEntry, Conversation

User = get_user_model()
PASSWORD = "Str0ng-Passw0rd!"
RESULT = {
    "status": "answered",
    "answer": "Registration closes on 15 March.",
    "message": None,
    "contactLine": None,
    "sources": [{"title": "Calendar", "url": None, "section": "Dates",
                 "page": 2, "date": "2026-01-15", "excerpt": "Closes 15 March."}],
}


def post(client, path, body, token=None):
    headers = {"HTTP_AUTHORIZATION": f"Token {token}"} if token else {}
    return client.post(path, json.dumps(body), content_type="application/json", **headers)


def get(client, path, token=None):
    headers = {"HTTP_AUTHORIZATION": f"Token {token}"} if token else {}
    return client.get(path, **headers)


class AuthTests(TestCase):
    def register(self, email="student@example.edu", password=PASSWORD, name="Student"):
        return post(self.client, "/api/auth/register/", {
            "email": email, "password": password, "name": name,
        })

    def test_register_creates_hashed_account_and_returns_token(self):
        r = self.register()
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertTrue(body["token"])
        self.assertEqual(body["user"], {"id": body["user"]["id"], "email": "student@example.edu", "name": "Student"})
        user = User.objects.get(username="student@example.edu")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_duplicate_email_is_rejected_case_insensitively(self):
        self.register()
        r = self.register(email="STUDENT@example.edu")
        self.assertEqual(r.status_code, 400)
        self.assertIn("already exists", r.json()["message"])

    def test_weak_password_is_rejected(self):
        r = self.register(password="123")
        self.assertEqual(r.status_code, 400)
        self.assertIn("password", json.dumps(r.json()).lower())

    def test_login_accepts_correct_credentials_and_rejects_wrong_ones(self):
        self.register()
        ok = post(self.client, "/api/auth/login/", {"email": "student@example.edu", "password": PASSWORD})
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.json()["token"])
        bad = post(self.client, "/api/auth/login/", {"email": "student@example.edu", "password": "wrong-password"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.json()["message"], "Incorrect email or password.")

    def test_me_requires_a_token_and_returns_the_user(self):
        self.assertEqual(get(self.client, "/api/auth/me/").status_code, 401)
        token = self.register().json()["token"]
        body = get(self.client, "/api/auth/me/", token=token).json()
        self.assertEqual(body["email"], "student@example.edu")

    def test_logout_revokes_the_token(self):
        token = self.register().json()["token"]
        self.assertEqual(post(self.client, "/api/auth/logout/", {}, token=token).status_code, 204)
        self.assertEqual(get(self.client, "/api/auth/me/", token=token).status_code, 401)


class HistoryTests(TestCase):
    def setUp(self):
        self.token = post(self.client, "/api/auth/register/", {
            "email": "student@example.edu", "password": PASSWORD,
        }).json()["token"]

    def create(self, question="When does registration close?", conversation=None):
        body = {"question": question, "result": RESULT}
        if conversation is not None:
            body["conversation"] = conversation
        return post(self.client, "/api/history/", body, token=self.token)

    def test_history_survives_logout_and_login(self):
        response = self.create()
        chat_id = response.json()["conversation"]["id"]

        logout = post(self.client, "/api/auth/logout/", {}, token=self.token)
        self.assertEqual(logout.status_code, 204)

        login = post(self.client, "/api/auth/login/", {
            "email": "student@example.edu", "password": PASSWORD,
        })
        self.assertEqual(login.status_code, 200)

        body = get(self.client, "/api/history/", token=login.json()["token"]).json()
        self.assertEqual([chat["title"] for chat in body], ["When does registration close?"])
        detail = get(self.client, f"/api/history/{chat_id}/", token=login.json()["token"]).json()
        self.assertEqual([entry["question"] for entry in detail["entries"]], ["When does registration close?"])

    def test_history_requires_authentication(self):
        self.assertEqual(get(self.client, "/api/history/").status_code, 401)
        self.assertEqual(post(self.client, "/api/history/", {"question": "Q", "result": RESULT}).status_code, 401)

    def test_new_chats_are_listed_newest_first_with_a_title(self):
        first = self.create("First question")
        second = self.create("Second question")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        body = get(self.client, "/api/history/", token=self.token).json()
        self.assertEqual([chat["title"] for chat in body], ["Second question", "First question"])
        self.assertEqual([chat["entry_count"] for chat in body], [1, 1])

    def test_questions_append_to_the_same_chat_file(self):
        first = self.create("First question")
        chat_id = first.json()["conversation"]["id"]
        second = self.create("Second question", conversation=chat_id)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["conversation"]["id"], chat_id)
        self.assertEqual(second.json()["conversation"]["entry_count"], 2)

        chats = get(self.client, "/api/history/", token=self.token).json()
        self.assertEqual(len(chats), 1)
        self.assertEqual(chats[0]["title"], "First question")
        self.assertEqual(chats[0]["entry_count"], 2)

        detail = get(self.client, f"/api/history/{chat_id}/", token=self.token).json()
        self.assertEqual(
            [entry["question"] for entry in detail["entries"]],
            ["First question", "Second question"],
        )

    def test_long_question_is_truncated_for_the_sidebar(self):
        chat = self.create("x" * 100).json()["conversation"]
        self.assertEqual(len(chat["title"]), 80)
        self.assertTrue(chat["title"].endswith("..."))

    def test_chat_can_be_read_and_deleted(self):
        chat_id = self.create().json()["conversation"]["id"]
        fetched = get(self.client, f"/api/history/{chat_id}/", token=self.token)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["entries"][0]["result"]["status"], "answered")
        self.assertEqual(self.client.delete(
            f"/api/history/{chat_id}/", HTTP_AUTHORIZATION=f"Token {self.token}"
        ).status_code, 204)
        self.assertEqual(get(self.client, f"/api/history/{chat_id}/", token=self.token).status_code, 404)
        self.assertFalse(ChatEntry.objects.exists())
        self.assertFalse(Conversation.objects.exists())

    def test_history_is_private_to_its_owner(self):
        chat_id = self.create().json()["conversation"]["id"]
        other = post(self.client, "/api/auth/register/", {
            "email": "other@example.edu", "password": PASSWORD,
        }).json()["token"]
        self.assertEqual(get(self.client, f"/api/history/{chat_id}/", token=other).status_code, 404)
        self.assertEqual(get(self.client, "/api/history/", token=other).json(), [])

    def test_cannot_append_to_another_users_chat(self):
        chat_id = self.create().json()["conversation"]["id"]
        other = post(self.client, "/api/auth/register/", {
            "email": "other@example.edu", "password": PASSWORD,
        }).json()["token"]
        response = post(self.client, "/api/history/", {
            "question": "Private append", "result": RESULT, "conversation": chat_id,
        }, token=other)
        self.assertEqual(response.status_code, 400)
        self.assertIn("not found", response.json()["message"])

    def test_clear_removes_only_the_callers_chats(self):
        self.create()
        self.assertEqual(self.client.delete(
            "/api/history/", HTTP_AUTHORIZATION=f"Token {self.token}"
        ).status_code, 204)
        self.assertEqual(get(self.client, "/api/history/", token=self.token).json(), [])

    def test_invalid_result_is_rejected(self):
        r = post(self.client, "/api/history/", {"question": "Q", "result": {"status": "invented"}}, token=self.token)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(ChatEntry.objects.exists())
        self.assertFalse(Conversation.objects.exists())
