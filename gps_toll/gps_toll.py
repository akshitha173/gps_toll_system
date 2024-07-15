import simpy
import geopandas as gpd
from shapely.geometry import Point, LineString
import pandas as pd
import matplotlib.pyplot as plt
import folium
import webbrowser
import tkinter as tk
from tkinter import messagebox

# Constants
SIMULATION_TIME = 100  # Simulation time in minutes
SIM_SPEED = 60  # Speed of simulation (km/h)

# List to collect alerts
alerts = []

# Function to collect payment alerts
def collect_payment_alert(vehicle_id, toll, balance):
    alert_message = f"Vehicle {vehicle_id}: Toll = {toll:.2f} Rs, Remaining Balance = {balance:.2f} Rs"
    alerts.append(alert_message)

# Function to show all collected alerts at once
def show_all_payment_alerts():
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    all_alerts_message = "\n".join(alerts)
    messagebox.showinfo("Payment Alerts", all_alerts_message)
    root.destroy()

# Function to show summary message
def show_summary_message(df):
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    summary_message = "Simulation Summary:\n\n" + df.to_string(index=False)
    messagebox.showinfo("Summary", summary_message)
    root.destroy()

class TollZone:
    def __init__(self, zone_id, location, rate_per_km):
        self.id = zone_id
        self.location = location.buffer(0.01)  # Creating a buffer around the location
        self.rate_per_km = rate_per_km

class User:
    def __init__(self, user_id, balance, vehicle_type, distance):
        self.id = user_id
        self.balance = balance
        self.vehicle_type = vehicle_type
        self.distance = distance

class Vehicle:
    def __init__(self, env, vehicle_id, start_location, end_location, user):
        self.env = env
        self.vehicle_id = vehicle_id
        self.start_location = start_location
        self.end_location = end_location
        self.route = LineString([self.start_location, self.end_location])
        self.distance_traveled = 0
        self.current_location = start_location
        self.user = user
        self.toll_incurred = 0  # Total toll incurred
        self.action = env.process(self.move())

    def move(self):
        while self.distance_traveled < self.user.distance:
            yield self.env.timeout(1)  # Move every 1 minute in simulation time
            self.distance_traveled += SIM_SPEED / 60  # Update distance traveled (km per minute)
            self.current_location = self.route.interpolate(self.distance_traveled / self.route.length, normalized=True)
            current_toll = self.calculate_toll()
            self.user.balance -= current_toll
            self.toll_incurred += current_toll  # Accumulate the toll incurred
            print(f"Vehicle {self.vehicle_id}: Distance Traveled = {self.distance_traveled:.2f} km, Toll = {current_toll:.2f} Rs, User Balance = {self.user.balance:.2f} Rs")
            collect_payment_alert(self.vehicle_id, current_toll, self.user.balance)

    def calculate_toll(self):
        total_toll = 0
        for zone in SimulationManager.toll_zones:
            if self.route.intersects(zone.location):
                intersected = self.route.intersection(zone.location)
                if isinstance(intersected, LineString):
                    distance_in_zone = intersected.length
                    toll = distance_in_zone * zone.rate_per_km
                    total_toll += toll

        # Adjust toll rates for different users
        if self.user.vehicle_type == 'truck':
            total_toll *= 50  # Example discount rate
        elif self.user.vehicle_type == 'motorcycle':
            total_toll *= 80  # Example surcharge rate
        elif self.user.vehicle_type =='car':
             total_toll *= 60
        return total_toll
      

class SimulationManager:
    toll_zones = [
        TollZone(1, Point(77.5899, 12.9716), 5),
        TollZone(2, Point(77.5946, 12.9781), 7),
        TollZone(3, Point(77.5800, 12.9750), 6),
        TollZone(4, Point(77.5850, 12.9680), 8)
    ]

    users = [
        User(1, 5000, 'truck', 5.0),
        User(2, 6000, 'motorcycle', 8.5),
        User(3, 7000, 'car', 6.2)
    ]

    @staticmethod
    def run_simulation():
        env = simpy.Environment()
        vehicles = [
            Vehicle(env, 1, Point(77.5806, 12.9721), Point(77.5946, 12.9781), SimulationManager.users[0]),
            Vehicle(env, 2, Point(77.5900, 12.9723), Point(77.5899, 12.9716), SimulationManager.users[1]),
            Vehicle(env, 3, Point(77.5950, 12.9700), Point(77.5920, 12.9740), SimulationManager.users[2])
        ]

        env.run(until=SIMULATION_TIME)

        # Collect data for all vehicles
        data = {
            'Vehicle ID': [v.vehicle_id for v in vehicles],
            'Distance Traveled': [v.distance_traveled for v in vehicles],
            'Toll Incurred': [v.toll_incurred for v in vehicles],
            'Remaining Balance': [v.user.balance for v in vehicles]
        }

        df = pd.DataFrame(data)
        print(df)

        # Show all payment alerts at once
        show_all_payment_alerts()

        # Visualization (Folium map)
        m = folium.Map(location=[12.9716, 77.5946], zoom_start=14)

        # Mark toll zones on the map
        for zone in SimulationManager.toll_zones:
            folium.Marker([zone.location.centroid.y, zone.location.centroid.x],
                          tooltip=f"Toll Zone {zone.id}").add_to(m)

        # Plot vehicle routes and their types
        vehicle_icons = {
            'truck': 'truck',
            'motorcycle': 'motorcycle',
            'car': 'car'
        }

        for vehicle in vehicles:
            icon = vehicle_icons.get(vehicle.user.vehicle_type, 'car')  # Default to car icon if type not found
            folium.Marker([vehicle.start_location.y, vehicle.start_location.x],
                          icon=folium.Icon(color='blue', icon=icon, prefix='fa'),
                          tooltip=f"Vehicle {vehicle.vehicle_id} (Start)").add_to(m)
            folium.Marker([vehicle.end_location.y, vehicle.end_location.x],
                          icon=folium.Icon(color='green', icon=icon, prefix='fa'),
                          tooltip=f"Vehicle {vehicle.vehicle_id} (End)").add_to(m)
            folium.PolyLine(locations=[(point[1], point[0]) for point in list(vehicle.route.coords)],
                            color='blue', weight=2.5, opacity=1).add_to(m)

        # Save map as HTML file and open it in default web browser
        m.save('simulation_map.html')
        webbrowser.open('simulation_map.html')

        # Visualization of data in graphs
        plt.figure(figsize=(10, 5))
        plt.subplot(1, 3, 1)
        plt.bar(df['Vehicle ID'], df['Distance Traveled'])
        plt.xlabel('Vehicle ID')
        plt.ylabel('Distance Traveled (km)')
        plt.title('Distance Traveled by Vehicles')

        plt.subplot(1, 3, 2)
        plt.bar(df['Vehicle ID'], df['Toll Incurred'])
        plt.xlabel('Vehicle ID')
        plt.ylabel('Toll Incurred (Rupees)')
        plt.title('Toll Incurred by Vehicles')

        plt.subplot(1, 3, 3)
        plt.bar(df['Vehicle ID'], df['Remaining Balance'])
        plt.xlabel('Vehicle ID')
        plt.ylabel('Remaining Balance (Rupees)')
        plt.title('Remaining Balance for Users')

        plt.tight_layout()
        plt.show()

        # Show summary message
        show_summary_message(df)

# Run the simulation
SimulationManager.run_simulation()