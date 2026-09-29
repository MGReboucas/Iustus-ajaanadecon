from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection, DatabaseError


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    """Liveness apenas: não comprova banco, jobs ou prontidão para produção."""
    return Response({"status": "ok"}, headers={"Cache-Control": "no-store"})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def readiness(request):
    """Banco acessível; exige proxy confiável e não revela detalhes da conexão."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return Response({"status": "unavailable"}, status=503, headers={"Cache-Control": "no-store"})
    return Response({"status": "ok"}, headers={"Cache-Control": "no-store"})
