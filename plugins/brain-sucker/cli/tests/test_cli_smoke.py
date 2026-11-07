from brainsuck.cli import main


def test_version_prints(capsys):
    assert main(["--version"]) == 0
    assert "0.1.0" in capsys.readouterr().out
