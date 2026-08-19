import archie.llm as llm

class DummyResponse:
    def raise_for_status(self):
        pass
    def json(self):
        return {"choices": [{"message": {"content": '{"ok": true}'}}]}

class DummyClient:
    last_payload = None
    def __init__(self, timeout=None):
        self.timeout = timeout
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def post(self, url, json=None):
        DummyClient.last_payload = json
        return DummyResponse()

def test_llama_json_and_thinking_contract(monkeypatch):
    monkeypatch.setattr(llm.httpx, "Client", DummyClient)
    out = llm.chat_json("system", "user")
    assert out == {"ok": True}
    p = DummyClient.last_payload
    assert p["response_format"] == {"type": "json_object"}
    assert p["chat_template_kwargs"] == {"enable_thinking": False}
    assert p["max_tokens"] > 0
