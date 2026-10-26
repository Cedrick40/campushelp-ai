import logging
import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from retrieval.generation import generate_answer
from retrieval.search import retrieve_evidence

from .models import ChatEntry, CorpusConfig, Document
from .serializers import (
    MAX_QUESTION_LENGTH,
    AskRequestSerializer,
    AskResponseSerializer,
    AuthResponseSerializer,
    ChatEntryCreateSerializer,
    ChatEntrySerializer,
    CorpusSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .validators import ERROR_MESSAGE, NOT_VERIFIED_MESSAGE, first_sentences, validate_generation

logger = logging.getLogger(__name__)
User = get_user_model()


def _user_payload(user):
    return {
        "id": user.pk,
        "email": user.email or user.username,
        "name": user.first_name or "",
    }


def _auth_payload(user):
    token, _ = Token.objects.get_or_create(user=user)
    return {"token": token.key, "user": _user_payload(user)}


def _serializer_message(serializer):
    """Flatten DRF field errors into the single message the UI displays."""
    for errors in serializer.errors.values():
        if isinstance(errors, (list, tuple)) and errors:
            return str(errors[0])
        if errors:
            return str(errors)
    return "Invalid request."


def _config():
    return CorpusConfig.objects.first() or CorpusConfig()


def _contact_line():
    config = _config()
    if config.contact_office:
        return {"office": config.contact_office, "source": config.contact_source}
    return None


def _reply(status, answer=None, sources=None, message=None, contact_line=None):
    body = {"status": status, "answer": answer, "sources": sources or [], "message": message}
    if status == "insufficient_evidence":
        body["contact_line"] = contact_line
    return body


def _validation_message(serializer):
    errors = serializer.errors.get("question", [])
    if any(getattr(e, "code", "") == "max_length" for e in errors):
        return f"Please keep your question under {MAX_QUESTION_LENGTH} characters."
    return "Please enter a question."


def _source_cards(cited_ids, evidence):
    by_id = {
        str(p["source_id"]): p
        for p in evidence
        if isinstance(p, dict) and p.get("source_id") is not None
    }
    cards = []
    for source_id in cited_ids:
        passage = by_id.get(source_id)
        if passage is None:
            continue
        card = {
            "title": passage.get("title") or "Untitled document",
            "url": passage.get("url") or "",
            "section": passage.get("section") or "",
            "date": passage.get("date"),
            "checked_date": passage.get("checked_date"),
            "excerpt": first_sentences(passage.get("text", "")),
        }
        if passage.get("page") is not None:
            card["page"] = passage["page"]
        cards.append(card)
    return cards

@extend_schema(
    request=AskRequestSerializer,
    responses={200: AskResponseSerializer, 400: AskResponseSerializer, 502: AskResponseSerializer},
)
@api_view(["POST"])
def ask(request):
    """Answer a question from the approved documents, with sources, or say it cannot verify."""
    serializer = AskRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(_reply("error", message=_validation_message(serializer)), status=400)

    question = serializer.validated_data["question"].strip()

    try:
        retrieval_status, evidence = retrieve_evidence(question)
    except Exception:
        logger.exception("Retrieval failed")
        return Response(_reply("error", message=ERROR_MESSAGE), status=502)

    # Layer 1 of the honest fallback: retrieval found nothing convincing.
    if retrieval_status != "retrieved" or not evidence:
        return Response(_reply(
            "insufficient_evidence", message=NOT_VERIFIED_MESSAGE, contact_line=_contact_line()
        ))

    try:
        raw = generate_answer(evidence, question)
    except Exception:
        logger.exception("Answer generation failed")
        return Response(_reply("error", message=ERROR_MESSAGE), status=502)

    result = validate_generation(raw, evidence)

    if result["status"] == "error":
        return Response(_reply("error", message=result["message"]), status=502)

    if result["status"] == "insufficient_evidence":
        return Response(_reply(
            "insufficient_evidence", message=result["message"], contact_line=_contact_line()
        ))

    return Response(_reply(
        result["status"],
        answer=result["answer"],
        sources=_source_cards(result["cited_source_ids"], evidence),
        message=result["message"],
    ))


@extend_schema(exclude=True)
@api_view(["GET"])
def health(request):
    """Liveness probe for the deployment platform."""
    return Response({"status": "ok", "service": "campushelp-ai"})


@extend_schema(responses=CorpusSerializer)
@api_view(["GET"])
def corpus(request):
    """Banner data: sample or official, the university, and when it was last checked."""
    config = _config()
    return Response({
        "type": config.corpus_type,
        "university": config.university,
        "last_checked": config.last_checked.isoformat() if config.last_checked else None,
    })


def document_file(request, pk):
    """Serve a recorded document file. Only files inside documents/ are ever served."""
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        raise Http404("No such document")

    root = Path(settings.DOCUMENTS_DIR).resolve()
    relative = document.file_path
    if relative.startswith("documents/"):
        relative = relative[len("documents/"):]
    path = (root / relative).resolve()

    if not path.is_relative_to(root) or not path.is_file():
        raise Http404("File not available")

    if path.suffix.lower() in {".md", ".txt"}:
        content_type = "text/plain; charset=utf-8"
    else:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    return FileResponse(open(path, "rb"), content_type=content_type)

# --------------------------------------------------------------- accounts


@extend_schema(request=RegisterSerializer, responses={201: AuthResponseSerializer, 400: None})
@api_view(["POST"])
def register(request):
    """Create an account and return the token the SPA stores."""
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"message": _serializer_message(serializer)}, status=400)
    data = serializer.validated_data
    email = data["email"]

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=data["password"],
                first_name=data.get("name", "").strip(),
            )
    except IntegrityError:
        return Response(
            {"message": "An account with this email already exists."}, status=400
        )

    return Response(_auth_payload(user), status=201)


@extend_schema(request=LoginSerializer, responses={200: AuthResponseSerializer, 400: None})
@api_view(["POST"])
def login(request):
    """Exchange email and password for a token."""
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"message": _serializer_message(serializer)}, status=400)
    user = authenticate(
        request,
        username=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
    )
    if user is None:
        return Response({"message": "Incorrect email or password."}, status=400)
    return Response(_auth_payload(user))


@extend_schema(request=None, responses={204: None})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """Revoke the caller's token."""
    Token.objects.filter(user=request.user).delete()
    return Response(status=204)


@extend_schema(responses=UserSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """The signed-in user, used to restore a session on page load."""
    return Response(_user_payload(request.user))


# ---------------------------------------------------------------- history


@extend_schema(
    request=ChatEntryCreateSerializer,
    responses={200: ChatEntrySerializer(many=True), 201: ChatEntrySerializer},
)
@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def history(request):
    """List, save, or clear the signed-in user's saved answers."""
    if request.method == "GET":
        entries = ChatEntry.objects.filter(user=request.user)[:100]
        return Response(ChatEntrySerializer(entries, many=True).data)

    if request.method == "DELETE":
        ChatEntry.objects.filter(user=request.user).delete()
        return Response(status=204)

    serializer = ChatEntryCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"message": _serializer_message(serializer)}, status=400)
    entry = ChatEntry.objects.create(
        user=request.user,
        question=serializer.validated_data["question"],
        result=serializer.validated_data["result"],
    )
    return Response(ChatEntrySerializer(entry).data, status=201)


@extend_schema(responses=ChatEntrySerializer)
@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def history_detail(request, pk):
    """Read or delete one saved answer belonging to the caller."""
    entry = get_object_or_404(ChatEntry, pk=pk, user=request.user)
    if request.method == "DELETE":
        entry.delete()
        return Response(status=204)
    return Response(ChatEntrySerializer(entry).data)
