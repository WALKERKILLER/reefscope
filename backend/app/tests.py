from django.test import SimpleTestCase


class HealthTests(SimpleTestCase):
    def test_get_health_without_model(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_is_read_only(self):
        self.assertEqual(self.client.post("/api/health").status_code, 405)

    def test_legacy_task_route(self):
        from django.urls import resolve
        self.assertEqual(resolve("/api/tasks").url_name, "task-list")
