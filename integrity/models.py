from django.core.validators import RegexValidator
from django.db import models


class Component(models.Model):
    name = models.CharField("Имя компонента", max_length=100, unique=True)
    version = models.CharField("Версия", max_length=32, default="1.0")
    expected_hash = models.CharField(
        "Доверенный SHA-256",
        max_length=64,
        validators=[RegexValidator(
            regex=r"\A[0-9a-f]{64}\Z",
            message="Укажи SHA-256: 64 символа от 0 до 9 и от a до f.",
        )],
    )
    created_at = models.DateTimeField("Дата регистрации", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Компонент"
        verbose_name_plural = "Компоненты"

    def __str__(self):
        return f"{self.name} — {self.version}"


class CheckEvent(models.Model):
    component = models.ForeignKey(
        Component,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="checks",
    )
    component_name = models.CharField("Имя компонента", max_length=100)
    version = models.CharField("Версия", max_length=32, blank=True)
    expected_hash = models.CharField("Эталонный SHA-256", max_length=64, blank=True)
    actual_hash = models.CharField("Фактический SHA-256", max_length=64, blank=True)
    verdict = models.CharField(
        "Вердикт",
        max_length=20,
        choices=[
            ("TRUSTED", "TRUSTED"),
            ("UNTRUSTED", "UNTRUSTED"),
            ("VERIFICATION_ERROR", "VERIFICATION_ERROR"),
        ],
    )
    action = models.CharField(
        "Решение",
        max_length=10,
        choices=[("ALLOWED", "Разрешено"), ("BLOCKED", "Заблокировано")],
    )
    operation = models.CharField(
        "Операция",
        max_length=12,
        default="CHECK",
        choices=[("CHECK", "Проверка"), ("DEMO_START", "Учебный запуск")],
    )
    actor = models.CharField("Инициатор", max_length=150, default="anonymous")
    reason = models.TextField("Причина")
    created_at = models.DateTimeField("Время проверки", auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Событие проверки"
        verbose_name_plural = "Журнал проверок"

    def __str__(self):
          return f"{self.component_name}: {self.verdict}"