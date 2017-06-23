# Traveling Salesman Tools
## This set of tools allows someone to:
Work towards solving the travelling salesman with as many points as you want, granted you feel like
waiting for it to work.

It would be very useful for others to contribute other algorithms (I may add in google-maps tsp solver)
but finding out the best way to group latitide and longitude coordinates into group sizes that the API can
take will take a bit of time (I'm not an expert by any means)
<h3>Use the PostcodeIO class to:</h3>
<li>Feed in a list of as many postcodes as you want and get their latitude and longitude back</li>
<li>Return the response objects from http://postcodes.io</li>
<br>
<h3>Use the Gbuddy class to:</h3>
Feed in a list of latitudes and longitude tuples (along with whatever identidying key you want to use
and return the travel time and distance using the google maps distance matrix api. You will need an API key
please read about limits and charges you may incur with large datasets
<br>
<h3>Use the Delivery Node and Network Classes to:</h3>
Take advantage of the Gbuddy and PostcodeIO classes with very high level arguements that make
calculating the distances easily and return them in a concise dictionary.

The Delivery Network can take in as many calculated nodes as you want and combine them into one
pandas dataframe for easily analysis and export to excel.

The simanneal class example is from the simanneal example file and can be used to simulate the delivery network.


For example:

    from collections import defaultdict
    import random

    main = DeliveryNetwork() # This was already calculated (or read in from excel files already calculated)

    w = warehouses.loc[warehouses["current"] == 1, "origin_pcode"].unique().tolist()
    four = four.loc[four["origin_key"].isin(w)]
    main.frames_join([one, two, three, four])

    optimal = main.find_warehouse(main.delivery_network, warehouse_keys=w, drop_warehouses=True)



    def _do_it():
        want_these = ['dest_key', 'distance', 'origin_key']
        order = {}
        for ware in w:
            _l = optimal.loc[(
                (optimal["origin_optimal_warehouse_key"] == ware)&
                (optimal["dest_optimal_warehouse_key"] == ware)), want_these]
            _r = _l.copy()
            _r.loc[:, [
                'dest_key', 'origin_key', 'distance']
                   ] = _r.loc[:, ['origin_key','dest_key', 'distance']].values
            _slice = pd.concat([_l, _r], ignore_index=True)

            dictionary_matrix = defaultdict(dict)
            for i, r in _slice.iterrows():
                dictionary_matrix[r["origin_key"]][r["dest_key"]] = r["distance"]
                dictionary_matrix[r["dest_key"]][r["origin_key"]] = r["distance"]
                dictionary_matrix[r["origin_key"]][r["origin_key"]] = 0.0
                dictionary_matrix[r["dest_key"]][r["dest_key"]] = 0.0

            start = list(dictionary_matrix.keys())[random.randint(0, len(dictionary_matrix.keys()))]
            init_state = list(dictionary_matrix.keys())

            random.shuffle(init_state)

            tsp = TravellingSalesmanProblem(init_state, dictionary_matrix)
            auto_schedule = tsp.auto(minutes=2) # Adjust to longer the longer you have
            tsp.set_schedule(auto_schedule) # Makes it easier than using defaults
            tsp.copy_strategy = "slice"
            state, e = tsp.anneal()

            while state[0] != start:
                state = state[1:] + state[:1]

            order[ware] = state

        return order

    findings = _do_it()
    
This code won't work for you, but just shows you how you can construct a distance_matrix from
a dataframe to a dictionary to be used in the simulated annealing funciton.
