from rest_framework import status
from rest_framework.test import APITestCase

from apps.catastro.models import Provincia, Ciudad
from apps.catastro.models import Provincia, Ciudad


class TestModels(APITestCase):

    fixtures = ['lineas.json', 'recorridos.json', 'provincias.json', 'ciudades.json', 'calles.json']

    def test_provincias(self):
        """ Should add and return one Provincia """
        provincias = Provincia.objects.all()
        self.assertEqual(len(provincias), 1)
        self.assertEqual(provincias.first().nombre, "Buenos Aires")
