import pytest

from src.environment import load_local_environment


def test_precedence_and_literal_credentials(tmp_path):
    (tmp_path / ".env").write_text("KEY=base\nONLY=first\nLITERAL=$(touch sentinel)\n")
    (tmp_path / ".env.local").write_text('KEY="local"\nQUOTED="a\\\\b"\nSINGLE=\'${HOME}\'\n')
    env = {"KEY": "process"}
    load_local_environment(tmp_path, env)
    assert env == {
        "KEY": "process",
        "ONLY": "first",
        "LITERAL": "$(touch sentinel)",
        "QUOTED": "a\\b",
        "SINGLE": "${HOME}",
    }
    assert not (tmp_path / "sentinel").exists()
    other = {}
    load_local_environment(tmp_path, other)
    assert other["KEY"] == "local"


@pytest.mark.parametrize("entry", ['KEY="SECRET', "export KEY=SECRET", 'KEY="SECRET\\n"'])
def test_errors_do_not_disclose_values_or_partially_load(tmp_path, entry):
    (tmp_path / ".env.local").write_text("OK=value\n" + entry)
    env = {}
    with pytest.raises(ValueError) as error:
        load_local_environment(tmp_path, env)
    assert "SECRET" not in str(error.value)
    assert not env
