import googlemaps
import requests


class PostcodeIO:
    url = "http://api.postcodes.io/postcodes"

    def chunk_generator(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def get_lat_lon(postcodes):

        responses = []
        lat_lons = []

        if type(postcodes) == str:
            postcodes = [postcodes]

        if type(postcodes) == list:
            safe_postcodes = list(PostcodeIO.chunk_generator(postcodes, 100))

        for chunk in safe_postcodes:

            response = requests.post(
                PostcodeIO.url,
                json={"postcodes": chunk}
            ).json()["result"]

            responses.append(response)
            for r in response:
                if r["result"]:
                    lat_lons.append(
                        (r["query"],
                         r["result"]["latitude"],
                         r["result"]["longitude"])
                    )
                else:
                    lat_lons.append((r["query"], None, None))

        return responses, lat_lons


class Gbuddy:

    def __init__(self, origins, destinations, api_key):

        self._origin_longer = len(origins) >= len(destinations)
        self._size = len(origins) * len(destinations) >= 100

        if self._size and self._origin_longer:
            self.origins = list(Gbuddy.chunk_generator(origins, 25))
            self.destinations = list(Gbuddy.chunk_generator(destinations, 4))
        elif self._size and not self._origin_longer:
            self.origins = list(Gbuddy.chunk_generator(origins, 4))
            self.destinations = list(Gbuddy.chunk_generator(destinations, 25))
        else:
            self.origins = list(Gbuddy.chunk_generator(origins, 25))
            self.destinations = list(Gbuddy.chunk_generator(destinations, 25))

        self.optimal_responses = []
        self.request_counter = 0
        self.test_counter = 0
        self.google_maps = googlemaps.Client(key=api_key)
        self.pairs = []

    def chunk_generator(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def get_optimal(self):
        for o in self.origins:
            for d in self.destinations:
                _response = self.google_maps.distance_matrix(
                    origins=o,
                    destinations=d,
                    units="imperial"
                )
                self.pairs.append((o, d))
                self.optimal_responses.append(_response)
                self.request_counter += 1

    def test_get_optimal(self):
        total_elements = 0
        for o in self.origins:
            for d in self.destinations:
                self.test_counter += 1
                print(len(o), len(d), len(o) * len(d))
                total_elements += len(o) * len(d)
        print(f"Requests Necessary: {self.test_counter}")
        print(f"Total Elements Generated: {total_elements}")
        self.reset_test_counter()

    def reset_test_counter(self):
        self.test_counter = 0

    def response_to_dict(self, response=None, destinations=None, origins=None):

        if not response:
            response = self.optimal_responses

        if not destinations:
            destinations = self.destinations

        if not origins:
            origins = self.origins

        self.response_dict = {
            "origin_name": [],
            "origin_lat": [],
            "origin_lon": [],
            "dest_lat": [],
            "dest_lon": [],
            "dest_name": [],
            "distance": [],
            "time": []
        }

        pairs = []
        for o in origins:
            for d in destinations:
                pairs.append((o, d))

        for r, p in zip(response, pairs):
            for x, y, z in zip(r["origin_addresses"],
                               r["rows"], p[0]):
                for A, B, C in zip(
                    r["destination_addresses"],
                    p[1],
                    y["elements"]
                ):
                    self.response_dict["origin_name"].append(x)
                    self.response_dict["origin_lat"].append(z[0])
                    self.response_dict["origin_lon"].append(z[1])
                    self.response_dict["dest_lat"].append(B[0])
                    self.response_dict["dest_lon"].append(B[1])
                    self.response_dict["dest_name"].append(A)
                    self.response_dict["distance"].append(
                        C["distance"]["value"])
                    self.response_dict["time"].append(C["duration"]["value"])
        return self.response_dict
