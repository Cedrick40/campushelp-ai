from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import ChatEntry, Conversation
from .validators import ALLOWED_STATUSES

MAX_QUESTION_LENGTH = 500
User = get_user_model()


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    name = serializers.CharField(allow_blank=True)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return email

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().lower()


class AuthResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserSerializer()


class ChatEntryCreateSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=MAX_QUESTION_LENGTH)
    result = serializers.JSONField()
    conversation = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate_question(self, value):
        question = value.strip()
        if not question:
            raise serializers.ValidationError("Please enter a question.")
        return question

    def validate_result(self, value):
        if not isinstance(value, dict) or value.get("status") not in ALLOWED_STATUSES:
            raise serializers.ValidationError("The stored answer is not valid.")
        return value

    def validate_conversation(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        if request is None or not Conversation.objects.filter(
            pk=value, user=request.user
        ).exists():
            raise serializers.ValidationError("That saved chat was not found.")
        return value


class ChatEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatEntry
        fields = ["id", "conversation", "question", "result", "created_at"]


class ConversationSummarySerializer(serializers.ModelSerializer):
    entry_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at", "entry_count"]


class ConversationDetailSerializer(serializers.ModelSerializer):
    entries = ChatEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at", "entries"]


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