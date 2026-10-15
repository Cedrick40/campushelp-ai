from rest_framework import serializers


class AskRequestSerializer(serializers.Serializer):
    question = serializers.CharField()


class SourceSerializer(serializers.Serializer):
    title = serializers.CharField()
    url = serializers.URLField(allow_null=True)
    section = serializers.CharField(allow_null=True)
    page = serializers.IntegerField(allow_null=True)


class AskResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["answered", "insufficient_evidence", "error"])
    answer = serializers.CharField(allow_null=True)
    sources = SourceSerializer(many=True)
    message = serializers.CharField(allow_null=True)
