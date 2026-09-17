import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from . import views


class StreamDebateTests(TestCase):
	def setUp(self):
		self.factory = RequestFactory()
		self.user = User.objects.create_user(username="tester", password="password")

	@patch("Debate_app.views.Debate.objects.get_or_create")
	@patch("Debate_app.views.clarifier_node")
	def test_invalid_topic_does_not_create_history(self, clarifier_node, get_or_create):
		clarifier_node.return_value = {
			"input_type": "",
			"is_valid": False,
			"clarifier_attempts": 1,
		}
		request = self.factory.get("/app/stream/", {"topic": "gibberish"})
		request.user = self.user

		response = views.stream_debate(request)
		events = b"".join(response.streaming_content).decode()

		get_or_create.assert_not_called()
		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			json.loads(events.removeprefix("data: ").strip())["clarifier"]["is_valid"],
			False,
		)

	def test_missing_rounds_defaults_to_two(self):
		request = self.factory.get("/app/stream/", {"topic": "test"})
		request.user = self.user

		with patch("Debate_app.views.clarifier_node", return_value={"is_valid": False}):
			response = views.stream_debate(request)

		self.assertEqual(response.status_code, 200)

	def test_upload_without_document_returns_bad_request(self):
		request = self.factory.post("/app/upload/")
		request.user = self.user

		response = views.upload_document(request)

		self.assertEqual(response.status_code, 400)

	@patch("Debate_app.views.set_vector_store")
	@patch("Debate_app.views.build_vector_store")
	@patch("Debate_app.views.chunk_document", return_value=["chunk"])
	@patch("Debate_app.views.load_document", return_value=iter(["document"]))
	def test_upload_preserves_file_extension_for_rag_loader(
		self, load_document, chunk_document, build_vector_store, set_vector_store):
		uploaded_file = SimpleUploadedFile(
			"notes.txt", b"debate context", content_type="text/plain"
		)
		request = self.factory.post(
			"/app/upload/", {"document": uploaded_file}
		)
		request.user = self.user

		response = views.upload_document(request)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(load_document.call_args.args[0].endswith(".txt"))
		chunk_document.assert_called_once()
		build_vector_store.assert_called_once_with(["chunk"])
		set_vector_store.assert_called_once_with(build_vector_store.return_value)

	def test_history_detail_requires_debate_ownership(self):
		other_user = User.objects.create_user(username="other", password="password")
		from .models import Debate
		debate = Debate.objects.create(thread_id="private-thread", user=other_user, topic="private")

		request = self.factory.get(f"/app/history/{debate.thread_id}/")
		request.user = self.user

		response = views.history_detail_view(request, debate.thread_id)

		self.assertEqual(response.status_code, 404)
