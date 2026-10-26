import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def group_existing_entries(apps, schema_editor):
    ChatEntry = apps.get_model("api", "ChatEntry")
    Conversation = apps.get_model("api", "Conversation")

    for entry in ChatEntry.objects.order_by("id").iterator():
        conversation = Conversation.objects.create(
            user_id=entry.user_id,
            title=entry.question[:120],
        )
        Conversation.objects.filter(pk=conversation.pk).update(
            created_at=entry.created_at,
            updated_at=entry.created_at,
        )
        entry.conversation_id = conversation.pk
        entry.save(update_fields=["conversation"])


def unlink_existing_entries(apps, schema_editor):
    ChatEntry = apps.get_model("api", "ChatEntry")
    Conversation = apps.get_model("api", "Conversation")
    ChatEntry.objects.update(conversation=None)
    Conversation.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_chatentry"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddField(
            model_name="chatentry",
            name="conversation",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="entries", to="api.conversation"),
        ),
        migrations.RunPython(group_existing_entries, unlink_existing_entries),
        migrations.AlterField(
            model_name="chatentry",
            name="conversation",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entries", to="api.conversation"),
        ),
        migrations.AlterModelOptions(
            name="chatentry",
            options={"ordering": ["created_at", "id"]},
        ),
    ]
