from rest_framework import serializers

MAX_QUESTION_LENGTH = 500


class AskRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=MAX_QUESTION_LENGTH)


class SourceSerializer(serializers.Serializer):
    title = serializers.CharField()
    url = serializers.CharField(help_text="Public URL, or /api/documents/<id>/file/ for sample documents")
    section = serializers.CharField(allow_blank=True)
    page = serializers.IntegerField(required=False, help_text="Omitted when the document has no pages")
    date = serializers.CharField(allow_null=True, help_text="Publication date, YYYY-MM-DD")
    checked_date = serializers.CharField(allow_null=True, help_text="Date the team last checked the source")
    excerpt = serializers.CharField()


class ContactLineSerializer(serializers.Serializer):
    office = serializers.CharField()
    source = serializers.CharField()


class AskResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["answered", "insufficient_evidence", "conflicting_sources", "error"]
    )
    answer = serializers.CharField(allow_null=True)
    sources = SourceSerializer(many=True)
    message = serializers.CharField(allow_null=True)
    contact_line = ContactLineSerializer(required=False, allow_null=True)


class CorpusSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["sample", "official"])
    university = serializers.CharField()
    last_checked = serializers.CharField(allow_null=True)