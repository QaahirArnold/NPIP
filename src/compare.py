import sqlite3
import pandas as pd

# Connect to the SQLite database
conn = sqlite3.connect('network_performance.db')
c = conn.cursor()

# Function to get the list of available cities
def get_available_cities():
    query = """SELECT DISTINCT city FROM (SELECT city FROM Download_Data 
                                           UNION 
                                           SELECT city FROM Upload_Data)"""
    cities = pd.read_sql_query(query, conn)
    return cities['city'].tolist()

# Function to get networks by city
def get_networks_by_city(city):
    query = f"""SELECT DISTINCT isp FROM (SELECT isp FROM Download_Data WHERE city = '{city}' 
                                          UNION 
                                          SELECT isp FROM Upload_Data WHERE city = '{city}')"""
    networks = pd.read_sql_query(query, conn)
    return networks['isp'].tolist()

# Function to get common networks in two cities
def get_common_networks(city1, city2):
    query = f"""SELECT DISTINCT isp FROM (
                    SELECT isp FROM Download_Data WHERE city = '{city1}'
                    UNION 
                    SELECT isp FROM Upload_Data WHERE city = '{city1}'
                )
                INTERSECT
                SELECT DISTINCT isp FROM (
                    SELECT isp FROM Download_Data WHERE city = '{city2}'
                    UNION 
                    SELECT isp FROM Upload_Data WHERE city = '{city2}'
                )"""
    networks = pd.read_sql_query(query, conn)
    return networks['isp'].tolist()

# Function to compare networks in one city with download speed, upload speed, and latency
def compare_networks_in_city(city, networks):
    # If no networks were selected, handle the "None" case gracefully
    if not networks or networks[0] == "None":
        print("No networks selected for comparison.")
        return
    
    # Construct the query with the fixed column ambiguity
    query = '''
        SELECT download.city, download.isp, 
               AVG(download.mbps) AS avg_download_mbps,
               AVG(upload.mbps) AS avg_upload_mbps,
               AVG(latency.latency) AS avg_latency
        FROM Download_Data AS download
        LEFT JOIN Upload_Data AS upload ON download.city = upload.city AND download.isp = upload.isp
        LEFT JOIN Latency_Data AS latency ON download.city = latency.city AND download.isp = latency.isp
        WHERE download.city = '{}'
        AND download.isp IN ({})
        GROUP BY download.city, download.isp
        ORDER BY avg_download_mbps DESC
    '''.format(city, ', '.join(["'{}'".format(isp) for isp in networks]))

    # Execute the query and fetch the results
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        print("No data found for the selected networks.")
    else:
        print(df)

# Function to compare one network in two cities with download speed, upload speed, and latency
def compare_network_between_cities(city1, city2, networks):
    # If no networks were selected, handle the "None" case gracefully
    if not networks or networks[0] == "None":
        print("No networks selected for comparison.")
        return

    # Print the cities and networks for debugging
    print(f"Comparing networks in cities: {city1} and {city2}")
    print(f"Selected networks: {networks}")

    # Construct the query with the fixed column ambiguity
    # Ensure network names are correctly formatted
    network_list = ", ".join(["'{}'".format(isp) for isp in networks])

    query = f'''
    SELECT download.city, download.isp, 
           AVG(download.mbps) AS avg_download_mbps,
           AVG(upload.mbps) AS avg_upload_mbps,
           AVG(latency.latency) AS avg_latency
    FROM Download_Data AS download
    LEFT JOIN Upload_Data AS upload
        ON download.city = upload.city AND download.isp = upload.isp
    LEFT JOIN Latency_Data AS latency
        ON download.city = latency.city AND download.isp = latency.isp
    WHERE download.city IN ('{city1}', '{city2}')
    AND download.isp IN ({network_list})
    GROUP BY download.city, download.isp
    ORDER BY download.city, avg_download_mbps DESC
    '''
    
    # Print the query for debugging
    #print("Executing query:")
    #print(query)

    # Execute the query and fetch the results
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        print("No data found for the selected networks.")
    else:
        print(df)

# Function to compare multiple networks in two cities with download speed, upload speed, and latency
def compare_multiple_networks_between_cities(cities, networks):
    if not cities or not networks:
        print("Cities or networks not selected.")
        return

    # Ensure there are at least two cities
    if len(cities) < 2:
        print("You must select exactly two cities.")
        return

    city1, city2 = cities

    # Construct the query with fully qualified column names
    query = f'''
    SELECT 
        download.city AS city,
        download.isp AS isp,
        AVG(download.mbps) AS avg_download_mbps,
        AVG(upload.mbps) AS avg_upload_mbps,
        AVG(latency.latency) AS avg_latency
    FROM Download_Data AS download
    LEFT JOIN Upload_Data AS upload 
        ON download.city = upload.city AND download.isp = upload.isp
    LEFT JOIN Latency_Data AS latency 
        ON download.city = latency.city AND download.isp = latency.isp
    WHERE download.city IN ('{city1}', '{city2}')
    AND download.isp IN ({', '.join(["'{}'".format(isp) for isp in networks])})
    GROUP BY download.city, download.isp
    ORDER BY download.city, avg_download_mbps DESC
    '''
    
    # Print the query for debugging
    print("Executing query:")
    print(query)

    # Execute the query and fetch the results
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        print("No data found for the selected networks.")
    else:
        print(df)

# Simple text interface for selection
def selection_menu():
    print("\nComparison Options:")
    print("1. Compare networks in your city")
    print("2. Compare a network between two cities")
    print("3. Compare multiple networks between two cities")

    choice = int(input("\nSelect an option (1-3): "))

    # Option 1: Compare networks in one city
    if choice == 1:
        cities = get_available_cities()
        print("\nAvailable Cities:")
        for i, city in enumerate(cities):
            print(f"{i + 1}. {city}")

        city_choice = int(input(f"\nSelect your city (1-{len(cities)}): "))
        selected_city = cities[city_choice - 1]

        networks = get_networks_by_city(selected_city)
        print(f"\nAvailable Networks in {selected_city}:")
        for i, network in enumerate(networks):
            print(f"{i + 1}. {network}")

        selected_networks = []
        for i in range(min(4, len(networks))):
            network_choice = input(f"\nSelect network {i + 1} (1-{len(networks)}, or 0 to stop): ")
            if network_choice == '0':
                break
            selected_networks.append(networks[int(network_choice) - 1])

        compare_networks_in_city(selected_city, selected_networks)

    # Option 2: Compare a network between two cities
    elif choice == 2:
        cities = get_available_cities()
        print("\nAvailable Cities:")
        for i, city in enumerate(cities):
            print(f"{i + 1}. {city}")

        city1_choice = int(input(f"\nSelect city 1 (1-{len(cities)}): "))
        city2_choice = int(input(f"\nSelect city 2 (1-{len(cities)}): "))

        # Ensure the selected choices are within the valid range
        if city1_choice < 1 or city1_choice > len(cities) or city2_choice < 1 or city2_choice > len(cities):
            print("Invalid city selection.")
            return

        selected_cities = [cities[city1_choice - 1], cities[city2_choice - 1]]

        common_networks = get_common_networks(selected_cities[0], selected_cities[1])
        if common_networks:
            print("\nCommon Networks in both cities:")
            for i, network in enumerate(common_networks):
                print(f"{i + 1}. {network}")

            network_choice = input(f"\nSelect a network (1-{len(common_networks)}, or 0 to stop): ")
            if network_choice != '0' and 1 <= int(network_choice) <= len(common_networks):
                # Pass the selected network as a list
                selected_network = [common_networks[int(network_choice) - 1]]
                compare_network_between_cities(selected_cities[0], selected_cities[1], selected_network)
            else:
                print("Invalid network selection or no network selected.")
        else:
            print("\nNo common networks available in the selected cities.")


    # Option 3: Compare multiple networks between two cities
    elif choice == 3:
        cities = get_available_cities()
        print("\nAvailable Cities:")
        for i, city in enumerate(cities):
            print(f"{i + 1}. {city}")

        city1_choice = int(input(f"\nSelect city 1 (1-{len(cities)}): "))
        city2_choice = int(input(f"\nSelect city 2 (1-{len(cities)}): "))

        selected_cities = [cities[city1_choice - 1], cities[city2_choice - 1]]

        networks_city1 = get_networks_by_city(selected_cities[0])
        networks_city2 = get_networks_by_city(selected_cities[1])

        selected_networks_city1 = []
        print(f"\nAvailable Networks in {selected_cities[0]}:")
        for i, network in enumerate(networks_city1):
            print(f"{i + 1}. {network}")
        for i in range(min(4, len(networks_city1))):
            network_choice = input(f"\nSelect network {i + 1} (1-{len(networks_city1)}, or 0 to stop): ")
            if network_choice == '0':
                break
            selected_networks_city1.append(networks_city1[int(network_choice) - 1])

        selected_networks_city2 = []
        print(f"\nAvailable Networks in {selected_cities[1]}:")
        for i, network in enumerate(networks_city2):
            print(f"{i + 1}. {network}")
        for i in range(min(4, len(networks_city2))):
            network_choice = input(f"\nSelect network {i + 1} (1-{len(networks_city2)}, or 0 to stop): ")
            if network_choice == '0':
                break
            selected_networks_city2.append(networks_city2[int(network_choice) - 1])

        selected_networks = list(set(selected_networks_city1) & set(selected_networks_city2))
        compare_multiple_networks_between_cities(selected_cities, selected_networks)

# Run the selection menu
selection_menu()

# Close the connection
conn.close()
