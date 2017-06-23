import requests
import googlemaps
import os
import json
import pandas as pd
import itertools as it
import random
from simanneal import Annealer


class PostcodeIO:
    url = "http://api.postcodes.io/postcodes"

    @staticmethod
    def chunk_generator(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    @staticmethod
    def get_lat_lon(postcodes):
        _responses = []
        _lat_lons = []

        if type(postcodes) == str:
            safe_postcodes = [[postcodes]]

        elif type(postcodes) == list:
            safe_postcodes = list(PostcodeIO.chunk_generator(postcodes, 100))

        else:
            try:
                safe_postcodes = list(
                    PostcodeIO.chunk_generator(postcodes, 100)
                )
            except Exception as e:
                print(e)

        for chunk in safe_postcodes:

            response = requests.post(
                PostcodeIO.url,
                json={"postcodes": chunk}
            ).json()["result"]

            _responses.append(response)
            for r in response:
                if r["result"]:
                    _lat_lons.append(
                        (r["query"],
                         r["result"]["latitude"],
                         r["result"]["longitude"])
                    )
                else:
                    _lat_lons.append((r["query"], None, None))
                    print(r["query"], "not found.")

        return _responses, _lat_lons


class DeliveryNode:

    def __init__(self,
                 postcode=None,
                 latitude=None,
                 longitude=None,
                 list_of_postcodes=[],
                 list_of_lat_lon_tuples=[],
                 is_warehouse=False
                 ):
        """Is warehouse dictates whether it will be a starting point"""

        self.postcode = postcode
        self.latitude = latitude
        self.longitude = longitude
        self.list_of_postcodes = list_of_postcodes
        self.list_of_lat_lon_tuples = list_of_lat_lon_tuples

    def get_node_coords(self, postcode=None):
        """If you have errors with this "import PostcodeIO"
         Only use for one postcode """
        if postcode:
            _, self.latitude, self.longitude = PostcodeIO.get_lat_lon(
                postcodes=postcode)[1][0]
            self.postcode = postcode
        elif self.postcode:
            _, self.latitude, self.longitude = PostcodeIO.get_lat_lon(
                postcodes=self.postcode)[1][0]
        else:
            print("You need to assign/pass-in a postcode")
            return None

    def add_postcodes(self, postcodes):
        """Feed in a list of postcodes of destinations"""
        if type(postcodes) == str:
            self.list_of_postcodes.append(postcodes)
        elif type(postcodes) in (list, tuple):
            self.list_of_postcodes.extend(postcodes)
        else:
            raise TypeError

    def calc_lat_lon_tuples(self):
        response, lat_lons = PostcodeIO.get_lat_lon(
            self.list_of_postcodes
        )
        self.list_of_lat_lon_tuples = [
            (y, z) for x, y, z in lat_lons
        ]

    def add_lat_lon_tuples(self, tuples):
        """Add either 1 tuple like (lat, lon) or a list of them
           like [(lat, lon), (lat, lon), ...]"""
        if type(tuples[0]) in (str, int, float):
            if len(tuples[0]) == 2:
                self.list_of_lat_lon_tuples.append(tuples)

        elif type(tuples[0]) == tuple:
            for t in tuples:
                if len(t) == 2:
                    self.list_of_lat_lon_tuples.append(t)

        else:
            print("""Add either 1 tuple like (lat, lon) or a list of them
                     like [(lat, lon), (lat, lon), ...]""")

    def verify_data_length(self):
        print(f"List of Tuples: {len(self.list_of_lat_lon_tuples)}")
        print(f"List of Postcodes: {len(self.list_of_postcodes)}")
        return len(self.list_of_lat_lon_tuples) == len(self.list_of_postcodes)

    def verify_list_of_tuples(self):
        """Makes sure all the tuples are length of two"""
        return all([len(x) == 2 for x in self.list_of_lat_lon_tuples])

    def add_financials(
        self,
        vehicle_mpg=20.0,
        monthly_warehouse_cost=0.0,
        monthly_wage=0.0,
        number_of_workers=1,
        number_of_vehicles=1,
        vehicle_owned=False
    ):
        self.vehicle_mpg = vehicle_mpg
        self.monthly_wage = monthly_wage
        self.monthly_warehouse_cost = monthly_warehouse_cost
        self.number_of_vehicles = number_of_vehicles
        self.number_of_workers = number_of_workers
        self.vehicle_owned = vehicle_owned

    def read_distances(self, filepath):
        """Read in JSON Object of previous findings"""
        try:
            with open(filepath, "r") as e:
                self.solved_distances = json.load(e)
        except Exception as e:
            print(f"Error: {e}")

    def calculate_distances(self, api_key, origin_keys=None, dest_keys=None):
        "Calculates Node lat_lon to all lat_lon_tuples location distance"
        if not origin_keys:
            origin_keys = [self.postcode]

        if not dest_keys:
            dest_keys = self.list_of_postcodes

        self.google_maps_matrix = Gbuddy(
            origins=[(self.latitude, self.longitude)],
            destinations=self.list_of_lat_lon_tuples,
            origin_keys=origin_keys,
            dest_keys=dest_keys
        )
        try:
            self.google_maps_matrix.get_optimal(api_key=api_key)
            self.solved_distances = self.google_maps_matrix.response_to_dict()
            print("Okay")
        except Exception as e:
            print(f"Error: {e}")

    def to_json(self, file_name=None, filepath=""):
        if file_name is None and self.postcode is not None:
            file_name = self.postcode

        elif file_name is None and self.postcode is None:
            file_name = "calculation"

        export_name = os.path.join(filepath, file_name + ".json")
        with open(export_name, 'w') as f:
            json.dump(self.google_maps_matrix.response_dict,
                      f, ensure_ascii=False)

    @staticmethod
    def node_to_node_paths(lat_lon_iterable):
        return list(it.combinations(lat_lon_iterable, 2))


class Gbuddy:

    def __init__(
        self,
        origins,
        destinations,
        origin_keys,
        dest_keys
    ):

        self._origin_longer = len(origins) >= len(destinations)
        self._size = len(origins) * len(destinations) >= 100

        if len(origin_keys) != len(origins):
            raise ValueError

        if self._size and self._origin_longer:
            self.origins = list(Gbuddy.chunk_generator(origins, 25))

            self.destinations = list(Gbuddy.chunk_generator(destinations, 4))
            self.dest_keys = list(Gbuddy.chunk_generator(dest_keys, 4))
        elif self._size and not self._origin_longer:
            self.origins = list(Gbuddy.chunk_generator(origins, 4))
            self.origin_keys = list(Gbuddy.chunk_generator(origin_keys, 4))
            self.destinations = list(Gbuddy.chunk_generator(destinations, 25))
            self.dest_keys = list(Gbuddy.chunk_generator(dest_keys, 25))
        else:
            self.origins = list(Gbuddy.chunk_generator(origins, 25))
            self.origin_keys = list(Gbuddy.chunk_generator(origin_keys, 25))
            self.destinations = list(Gbuddy.chunk_generator(destinations, 25))
            self.dest_keys = list(Gbuddy.chunk_generator(dest_keys, 25))

        self.optimal_responses = []
        self.request_counter = 0
        self.test_counter = 0
        self.pairs = []

    def chunk_generator(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def get_optimal(self, api_key):
        self.google_maps = googlemaps.Client(key=api_key)
        for o, ok in zip(self.origins, self.origin_keys):
            for d, dk in zip(self.destinations, self.dest_keys):
                _response = self.google_maps.distance_matrix(
                    origins=o,
                    destinations=d,
                    units="imperial"
                )
                self.pairs.append((o, d, ok, dk))
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

    def response_to_dict(self, responses=None):

        if not responses:
            responses = self.optimal_responses

        self.response_dict = {
            "origin_key": [],
            "origin_name": [],
            "origin_lat": [],
            "origin_lon": [],
            "dest_lat": [],
            "dest_lon": [],
            "dest_name": [],
            "dest_key": [],
            "distance": [],
            "time": []
        }

        for pair, response in zip(self.pairs, responses):
            for x, y, z in zip(pair[0], pair[2], response["origin_addresses"]):
                for a, b, c, d in zip(pair[1],
                                      pair[3],
                                      response["destination_addresses"],
                                      response["rows"][0]["elements"]):

                    self.response_dict["origin_key"].append(y)
                    self.response_dict["origin_name"].append(z)
                    self.response_dict["origin_lat"].append(x[0])
                    self.response_dict["origin_lon"].append(x[1])
                    self.response_dict["dest_key"].append(b)
                    self.response_dict["dest_name"].append(c)
                    self.response_dict["dest_lat"].append(a[0])
                    self.response_dict["dest_lon"].append(a[1])
                    self.response_dict["distance"].append(
                        d["distance"]["value"]
                    )
                    self.response_dict["time"].append(d["duration"]["value"])
        return self.response_dict


class DeliveryNetwork:
    "Delivery Nodes will be transformed into a pandas dataframe"

    def __init__(self, delivery_nodes=None, read_in=False, read_file=None):

        if read_in and read_file:
            try:
                self.delivery_network = pd.read_excel(f"{read_file}")
            except Exception as e:
                print(f"Error: {e}")
        elif delivery_nodes:
            self.delivery_nodes = [
                n for n in delivery_nodes if hasattr(n, "solved_distances")
            ]
            if len(delivery_nodes) == 1:
                self.delivery_network = pd.DataFrame.from_dict(
                    self.delivery_nodes[0].solved_distances
                )
            try:
                self.delivery_network = pd.concat(
                    [
                        pd.DataFrame.from_dict(node.solved_distances) for
                        node in self.delivery_nodes
                    ],
                    ignore_index=True
                )
            except Exception as e:
                print(f"Error: {e}")

    def network_to_excel(self, filename):
        "Need to pass either the 'filename.xlsx' or 'fullpath + filename.xlsx'"
        try:
            self.delivery_network.to_excel(f"{filename}", index=False)
        except Exception as e:
            print(e)

    @staticmethod
    def find_warehouse(left, warehouse_keys=[], sorter="distance",
                       drop_warehouses=False):
        _temp = left.loc[
            left["origin_key"].isin(warehouse_keys)
        ].sort_values(
            ["dest_key", sorter], ascending=True).drop_duplicates(
            "dest_key"
        )[["dest_key", "distance", "origin_key", "time"]]

        _temp.rename(columns={"distance": "distance_to_warehouse",
                              "origin_key": "dest_optimal_warehouse_key",
                              "time": "time_to_warehouse"}, inplace=True)

        a = left.merge(_temp, how="left",
                       left_on="dest_key", right_on="dest_key")

        a = DeliveryNetwork._clean_up(a)

        if drop_warehouses:
            a = a.loc[~a["origin_key"].isin(warehouse_keys)]

        return a

    @staticmethod
    def _clean_up(frame):
        _ = frame.drop_duplicates("dest_key")[[
            "dest_key", "dest_optimal_warehouse_key"
        ]]

        print(_)
        _.rename(columns={
            "dest_optimal_warehouse_key": "origin_optimal_warehouse_key",
            "dest_key": "origin_key"
        }, inplace=True)

        return frame.merge(
            _, how="left", left_on="origin_key", right_on="origin_key"
        )

    def frames_join(self, dataframes=[]):
        if len(dataframes) > 0:
            try:
                self.delivery_network = pd.concat(
                    dataframes, ignore_index=True)
            except Exception as e:
                print(f"{e}")

                
# Example taken by author of simanneal package I just use his/her auto config
# https://github.com/perrygeo/simanneal
class TravellingSalesmanProblem(Annealer):

    """Test annealer with a travelling salesman problem.
    """

    # pass extra data (the distance matrix) into the constructor
    def __init__(self, state, distance_matrix):
        self.distance_matrix = distance_matrix
        super(TravellingSalesmanProblem, self).__init__(state)  # important!

    def move(self):
        """Swaps two cities in the route."""
        a = random.randint(0, len(self.state) - 1)
        b = random.randint(0, len(self.state) - 1)
        self.state[a], self.state[b] = self.state[b], self.state[a]

    def energy(self):
        """Calculates the length of the route."""
        e = 0
        for i in range(len(self.state)):
            e += self.distance_matrix[self.state[i - 1]][self.state[i]]
        return e
