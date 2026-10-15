from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["POST"])
def ask(request):
    question = (request.data.get("question") or "").strip()
    if not question:
        return Response(
            {"status": "error", "answer": None, "sources": [],
             "message": "Please enter a question."},
            status=400,
        )
    return Response({
        "status": "answered",
        "answer": "This is a mock answer.",
        "sources": [{"title": "Mock source", "url": None, "section": None, "page": None}],
        "message": None,
    })
