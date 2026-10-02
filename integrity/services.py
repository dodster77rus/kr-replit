import hashlib
import os
import re
import stat

from django.conf import settings
from django.db import transaction

from .models import Component, CheckEvent


DEMO_DIR = settings.BASE_DIR / "demo_components"
DEMO_FILES = {
    "app.py": b'APP_NAME = "Integrity demo"\n',
    "auth.py": b"REQUIRE_AUTH = True\n",
    "config.yaml": b"debug: false\nrequire_auth: true\n",
}


def initialize_demo():
    DEMO_DIR.mkdir(exist_ok=True)
    if DEMO_DIR.is_symlink():
        raise ValueError("Папка demo_components должна быть обычной папкой.")

    for name, trusted_bytes in DEMO_FILES.items():
        try:
            with (DEMO_DIR / name).open("xb") as file:
                file.write(trusted_bytes)
        except FileExistsError:
            pass

        Component.objects.get_or_create(
            name=name,
            defaults={
                "version": "1.0",
                "expected_hash": hashlib.sha256(trusted_bytes).hexdigest(),
            },
        )

    return Component.objects.filter(name__in=DEMO_FILES)


def read_demo_file(name):
    if name not in DEMO_FILES:
        raise OSError("Компонент отсутствует в разрешённом списке.")
    directory_fd = os.open(
        DEMO_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    )
    try:
        file_fd = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory_fd,
        )
        with os.fdopen(file_fd, "rb") as file:
            if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
                raise OSError("Компонент должен быть обычным файлом.")
            data = file.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise OSError("Размер тестового файла превышает 1 МБ.")
            return data
    finally:
        os.close(directory_fd)


@transaction.atomic
def verify_component(name, actor="anonymous", operation="CHECK"):
    if operation not in {"CHECK", "DEMO_START"}:
        raise ValueError("Неизвестная операция.")

    name = str(name)[:100]
    component = None
    actual_hash = ""
    verdict = "VERIFICATION_ERROR"
    reason = "Компонент отсутствует в разрешённом списке."

    if name in DEMO_FILES:
        component = Component.objects.filter(name=name).first()
        if component is None:
            reason = "Доверенный эталон не зарегистрирован."
        elif not re.fullmatch(r"[0-9a-f]{64}", component.expected_hash):
            reason = "Доверенный эталон содержит некорректный SHA-256."
        else:
            try:
                actual_hash = hashlib.sha256(read_demo_file(name)).hexdigest()
                if actual_hash == component.expected_hash:
                    verdict = "TRUSTED"
                    reason = "Фактический SHA-256 совпадает с эталоном."
                else:
                    verdict = "UNTRUSTED"
                    reason = "Содержимое компонента изменено: SHA-256 не совпадает."
            except OSError:
                reason = "Файл отсутствует, недоступен или имеет недопустимый тип."

    return CheckEvent.objects.create(
        component=component,
        component_name=name,
        version=component.version if component else "",
        expected_hash=component.expected_hash if component else "",
        actual_hash=actual_hash,
        verdict=verdict,
        action="ALLOWED" if verdict == "TRUSTED" else "BLOCKED",
        operation=operation,
        actor=str(actor)[:150],
        reason=reason,
    )
