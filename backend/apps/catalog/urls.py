from django.urls import path

from . import views

urlpatterns = [
    path("catalog/countries", views.CountryListView.as_view(), name="catalog-countries"),
    path("catalog/institutions", views.InstitutionListView.as_view(), name="catalog-institutions"),
    path("catalog/programs", views.ProgramListView.as_view(), name="catalog-programs"),
    path("catalog/scholarship-types", views.ScholarshipTypeListView.as_view(), name="catalog-scholarship-types"),
]
