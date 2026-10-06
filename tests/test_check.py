from django.core.management import call_command


def test_system_check_passes() -> None:
    call_command("check", fail_level="WARNING")
