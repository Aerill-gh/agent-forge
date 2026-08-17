from agentcore.specs.decorators import registry, spec


def test_spec_decorator_records_in_registry() -> None:
    @spec("AGT-999")
    def some_agent_entrypoint() -> None:
        pass

    assert some_agent_entrypoint in registry["AGT-999"]
