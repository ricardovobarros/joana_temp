import os
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")
os.environ.setdefault("MQTT_HOST", "mqtt.example.com")
os.environ.setdefault("MQTT_USER", "test-user")
os.environ.setdefault("MQTT_PASS", "test-pass")

import main
import mqtt_bridge


NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


class AppTimersTest(unittest.TestCase):
    @patch.object(main.mqtt_bridge, "send_command", return_value=False)
    @patch.object(main.db, "start_session")
    @patch.object(main.db, "open_session", return_value=None)
    @patch.object(main.db, "now_utc", return_value=NOW)
    def test_timer_starts_even_when_mqtt_is_unavailable(
        self, _now, _open, start, send
    ):
        result = main.timer(main.TimerBody(action="start"))

        self.assertEqual(result, {"ok": True, "action": "start"})
        start.assert_called_once_with(NOW)
        send.assert_called_once_with("start")

    @patch.object(main.mqtt_bridge, "send_sleep_command", return_value=False)
    @patch.object(main.db, "insert_sleep_event")
    @patch.object(main.db, "now_utc", return_value=NOW)
    def test_sleep_is_recorded_even_when_mqtt_is_unavailable(
        self, _now, insert, send
    ):
        result = main.set_sleep(main.SleepBody(action="sleep"))

        self.assertEqual(result, {"ok": True, "action": "sleep"})
        insert.assert_called_once_with(NOW, "sleep", "app")
        send.assert_called_once_with("sleep")

    @patch.object(main.mqtt_bridge, "send_sleep_command", return_value=False)
    @patch.object(main.db, "insert_sleep_event")
    @patch.object(main.db, "now_utc", return_value=NOW)
    def test_wake_is_recorded_without_a_matching_sleep(self, _now, insert, _send):
        main.set_sleep(main.SleepBody(action="wake"))

        insert.assert_called_once_with(NOW, "wake", "app")

    @patch.object(main.mqtt_bridge, "send_command", return_value=False)
    @patch.object(main.db, "close_session")
    @patch.object(main.db, "open_session", return_value={"id": 7})
    @patch.object(main.db, "now_utc", return_value=NOW)
    def test_timer_stop_is_persisted_before_optional_mqtt(
        self, _now, _open, close, _send
    ):
        main.timer(main.TimerBody(action="stop"))

        close.assert_called_once_with({"id": 7}, NOW, "app")

    @patch.object(mqtt_bridge.db, "start_session")
    @patch.object(mqtt_bridge.db, "close_session")
    def test_stale_device_sync_does_not_change_app_timer(self, close, start):
        mqtt_bridge._handle_state(
            {"event": "sync", "running": False, "elapsed_s": 0}, retained=False
        )

        start.assert_not_called()
        close.assert_not_called()

    @patch.object(mqtt_bridge.db, "insert_sleep_event")
    def test_stale_sleep_sync_does_not_record_an_event(self, insert):
        mqtt_bridge._handle_sleep(
            {"event": "sync", "sleeping": False}, retained=False
        )

        insert.assert_not_called()

    @patch.object(mqtt_bridge.db, "now_utc", return_value=NOW)
    @patch.object(mqtt_bridge.db, "insert_sleep_event")
    def test_button_records_sleep_every_time(self, insert, _now):
        payload = {"event": "sleep", "sleeping": True, "reason": "button", "ago_s": 0}
        mqtt_bridge._handle_sleep(payload, retained=False)
        mqtt_bridge._handle_sleep(payload, retained=False)

        self.assertEqual(insert.call_count, 2)
        insert.assert_called_with(NOW, "sleep", "button")


if __name__ == "__main__":
    unittest.main()
