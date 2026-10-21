"""Per-profile WebAPI routing for the Relay chat channel.

The phone sends ``chat.send`` with a profile name. Relay must address the
profile, not the gateway's default profile: upstream serves each profile it
multiplexes under ``/p/<name>/...``. These tests pin the URL and credential
selection without touching the network.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from plugin.relay.channels.chat import ChatHandler


class ChatProfileRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.hermes_dir = Path(self._tmp.name)
        (self.hermes_dir / "config.yaml").write_text(
            "model:\n  default: x\n", encoding="utf-8"
        )
        (self.hermes_dir / "profiles" / "coder").mkdir(parents=True)
        (self.hermes_dir / "profiles" / "coder" / "config.yaml").write_text(
            "model:\n  default: x\n", encoding="utf-8"
        )
        self.config = SimpleNamespace(
            hermes_config_path=str(self.hermes_dir / "config.yaml")
        )

    def _handler(self) -> ChatHandler:
        return ChatHandler("http://gateway.test:8642", config=self.config)

    def test_default_profile_uses_gateway_root(self) -> None:
        handler = self._handler()
        self.assertEqual(
            handler._profile_webapi_url("default"),  # type: ignore[attr-defined]
            "http://gateway.test:8642",
        )
        self.assertEqual(
            handler._profile_webapi_url(""),  # type: ignore[attr-defined]
            "http://gateway.test:8642",
        )

    def test_served_profile_uses_scoped_route(self) -> None:
        handler = self._handler()
        with patch(
            "plugin.relay.config._profile_prefix_served", return_value=True
        ):
            self.assertEqual(
                handler._profile_webapi_url("coder"),  # type: ignore[attr-defined]
                "http://gateway.test:8642/p/coder",
            )

    def test_unserved_profile_falls_back_to_root(self) -> None:
        handler = self._handler()
        with patch(
            "plugin.relay.config._profile_prefix_served", return_value=False
        ):
            self.assertEqual(
                handler._profile_webapi_url("coder"),  # type: ignore[attr-defined]
                "http://gateway.test:8642",
            )

    def test_profile_api_key_prefers_profile_dotenv(self) -> None:
        (self.hermes_dir / "profiles" / "coder" / ".env").write_text(
            "API_SERVER_KEY=profile-key\n", encoding="utf-8"
        )
        (self.hermes_dir / ".env").write_text(
            "API_SERVER_KEY=root-key\n", encoding="utf-8"
        )
        handler = self._handler()
        self.assertEqual(
            handler._profile_api_key("coder"),  # type: ignore[attr-defined]
            "profile-key",
        )

    def test_profile_api_key_falls_back_to_shared_key(self) -> None:
        (self.hermes_dir / ".env").write_text(
            "API_SERVER_KEY=root-key\n", encoding="utf-8"
        )
        handler = self._handler()
        self.assertEqual(
            handler._profile_api_key("coder"),  # type: ignore[attr-defined]
            "root-key",
        )

    def test_handler_without_config_keeps_legacy_behaviour(self) -> None:
        handler = ChatHandler("http://gateway.test:8642")
        self.assertEqual(
            handler._profile_webapi_url("coder"),  # type: ignore[attr-defined]
            "http://gateway.test:8642",
        )


if __name__ == "__main__":
    unittest.main()
