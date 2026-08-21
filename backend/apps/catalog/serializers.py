from rest_framework import serializers

from .models import Country, Institution, Program, ScholarshipType


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "iso_code"]


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ["id", "name", "country"]


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ["id", "name", "institution", "academic_level"]


class ScholarshipTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScholarshipType
        fields = ["id", "name"]
