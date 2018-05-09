from rest_framework import status
from rest_framework.test import APITestCase

from apps.catastro.models import Provincia, Ciudad


class TestEndpoints(APITestCase):

    fixtures = ['lineas.json', 'recorridos.json', 'provincias.json', 'ciudades.json']

    def test_ciudades(self):
        """ Should add and return one Ciudad """
        response = self.client.get('/api/v3/ciudades/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nombre"], "La Plata")

    def test_lineas(self):
        """ Should add and return one Ciudad """
        response = self.client.get('/api/v3/lineas/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nombre"], "129 (plaza)")

    def test_recorridos_origen_destino(self):
        "should simulate a client query based on two points and return the only result"
        response = self.client.get(
            '/api/v3/recorridos/?l=-57.968416213989265%2C-34.910780590483675%2C300%7C-57.960262298583984%2C-34.9169742332207%2C300&c=la-plata&page=1&t=false&_=1525902459771')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.data)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["itinerario"][0]["nombre"], "129 (plaza) 1")

    def test_recorridos_por_linea(self):
        "should simulate a client query based on bus name"
        response = self.client.get(
            '/api/v3/recorridos/?q=129&c=la-plata&page=1&_=1525903762474')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.data)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["nombre"], "129 (plaza) 1")
