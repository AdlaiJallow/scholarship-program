from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Country, Institution, Program, ScholarshipType
from .serializers import CountrySerializer, InstitutionSerializer, ProgramSerializer, ScholarshipTypeSerializer


class CountryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CountrySerializer
    queryset = Country.objects.all()


class InstitutionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InstitutionSerializer
    queryset = Institution.objects.filter(is_active=True)


class ProgramListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProgramSerializer
    queryset = Program.objects.all()


class ScholarshipTypeListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ScholarshipTypeSerializer
    queryset = ScholarshipType.objects.filter(is_active=True)
