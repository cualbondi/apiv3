from rest_framework import status
from rest_framework.test import APITestCase

from apps.catastro.models import Provincia, Ciudad


class TestRecorridos(APITestCase):

    fixtures = ['lineas.json', 'recorridos.json', 'provincias.json', 'ciudades.json']

    def assert_recorrido(self, qstring, nombre):
        response = self.client.get(
            '/api/v3/recorridos/' + qstring)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["itinerario"][0]["nombre"], nombre)

    def assert_recorrido_con_trasbordo(self, qstring, linea1, linea2):
        response = self.client.get(
            '/api/v3/recorridos/' + qstring)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(result["itinerario"][0]["nombre"], linea1)
        self.assertEqual(result["itinerario"][1]["nombre"], linea2)

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

    def test_recorridos_origen_destino(self):
        "should simulate a client query based on two points and return the only result"
        self.assert_recorrido(
            '?l=-57.968416213989265%2C-34.910780590483675%2C300%7C-57.960262298583984%2C-34.9169742332207%2C300&c=la-plata&page=1&t=false', "129 (plaza) 1")

    def test_recorridos_por_linea_1(self):
        "should simulate a client query based on bus name"
        response = self.client.get(
            '/api/v3/recorridos/?q=129&c=la-plata&page=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["nombre"], "129 (plaza) 1")

    def test_recorridos_por_linea_sur(self):
        "should simulate a client query based on bus name"
        self.assert_recorrido(
            '?l=-57.985968589782715%2C-34.97164099922274%2C300%7C-57.98150539398193%2C-34.96773743901797%2C300&c=la-plata&page=1&t=false', "Sur 41")

        self.assert_recorrido(
            '?l=-57.985968589782715%2C-34.97164099922274%2C300%7C-57.9801321029663%2C-34.968616635473474%2C300&c=la-plata&page=1&t=false', "Sur 41")

        self.assert_recorrido(
            '?l=-57.984766960144036%2C-34.97255531976999%2C300%7C-57.9801321029663%2C-34.968616635473474%2C300&c=la-plata&page=1&t=false', "Sur 41")

        self.assert_recorrido(
            '?l=-57.984766960144036%2C-34.97255531976999%2C300%7C-57.981548309326165%2C-34.96780777508163%2C300&c=la-plata&page=1&t=false', "Sur 41")

    def test_recorridos_por_linea_fx1(self):
        "should simulate a client query based on bus name"
        self.assert_recorrido(
            '?l=-57.93554306030274%2C-34.91380708793209%2C300%7C-57.937173843383796%2C-34.91795954238727%2C300&c=la-plata&page=1&t=false', "202 Fx1")

        self.assert_recorrido(
            '?l=-57.88747787475585%2C-34.86522889452201%2C300%7C-57.937173843383796%2C-34.91795954238727%2C300&c=la-plata&page=1&t=false', "202 Fx1")

        self.assert_recorrido(
            '?l=-57.88747787475585%2C-34.86522889452201%2C300%7C-57.8982925415039%2C-34.880016602392146%2C300&c=la-plata&page=1&t=false', "202 Fx1")

        self.assert_recorrido(
            '?l=-57.886362075805664%2C-34.86558101371409%2C300%7C-57.89091110229492%2C-34.86649651655751%2C300&c=la-plata&page=1&t=false', "202 Fx1")

    def test_recorrido_con_trasbordo_129_202(self):
        self.assert_recorrido_con_trasbordo("?l=-58.137073516845696%2C-34.85156550582556%2C800%7C-57.88455963134766%2C-34.86452465161482%2C800&c=la-plata&page=1&t=true", "129 (plaza) 1", "202 Fx1")


# will test again if mocking geocoding urls
# class TestGeocoder(APITestCase):

#     fixtures = ['lineas.json', 'recorridos.json', 'provincias.json', 'ciudades.json', 'calles.json', 'zonas.json', 'pois.json']

#     def test_interseccion(self):
#         """ Should return one intersection """
#         response = self.client.get(
#             '/api/v3/geocoder/?q=12 y 62&c=la-plata')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)

#     def test_poi(self):
#         """ Should return one poi """
#         response = self.client.get(
#             '/api/v3/geocoder/?q=INIFTA - UNLP&c=la-plata')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)
