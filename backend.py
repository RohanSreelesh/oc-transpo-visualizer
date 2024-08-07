from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from google.transit import gtfs_realtime_pb2
import time
import json
from solace.messaging.config.retry_strategy import RetryStrategy
from solace.messaging import  message
from solace.messaging.messaging_service import MessagingService
from solace.messaging.resources.topic import Topic
from solace.messaging.config.solace_properties import transport_layer_properties, service_properties, authentication_properties
from solace.messaging.config.transport_security_strategy import TLS
from solace.messaging.config.authentication_strategy import BasicUserNamePassword
from dotenv import load_dotenv

import os

load_dotenv() 
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv('API_KEY')
VEHICLE_POSITIONS_URL = os.getenv('VEHICLE_POSITIONS_URL')

# Solace configuration
SOLACE_HOST = os.getenv('SOLACE_HOST')
SOLACE_VPN = os.getenv('SOLACE_VPN')
SOLACE_USERNAME = os.getenv('SOLACE_USERNAME')
SOLACE_PASSWORD = os.getenv('SOLACE_PASSWORD')

messaging_service = None

def initialize_broker():
    global messaging_service
    if messaging_service is None:
        try:
            
            broker_props = {
            transport_layer_properties.HOST: SOLACE_HOST,
            service_properties.VPN_NAME: SOLACE_VPN,
            }
            
            transport_security = TLS.create().without_certificate_validation()
            
            messaging_service = MessagingService.builder().from_properties(broker_props).with_transport_security_strategy(transport_security) \
            .with_authentication_strategy(BasicUserNamePassword.of(SOLACE_USERNAME, SOLACE_PASSWORD)) \
                .build().connect()
            messaging_service.connect()
            print("Connected to Solace")
        except Exception as e:
            print(f"Error connecting to Solace: {e}")


def publish_to_broker(grid_data):
    global messaging_service
    if messaging_service is None or not messaging_service.is_connected:
        initialize_broker()
    
    if messaging_service and messaging_service.is_connected:
        try:
            direct_publish_service = messaging_service.create_direct_message_publisher_builder()\
                .on_back_pressure_reject(buffer_capacity=0)\
                .build()
            
            pub_start = direct_publish_service.start_async()
            pub_start.result()  # Wait for the publisher to be ready
            
            for grid_cell, vehicles in grid_data.items():
                destination = Topic.of(f"buses/grid/{grid_cell}")
                print(f"vehicles : {str(json.dumps(vehicles))}")
                print("-----------------------------------")
                print(f"VEHINCLES WITHOUT JSON : {vehicles}")
                message = messaging_service.message_builder()\
                    .with_application_message_id("OC-TRANSPO-UPDATE")\
                    .build(json.dumps(vehicles))
                
                
                
                try:
                    direct_publish_service.publish(destination=destination, message=message)
                except Exception as e:
                    print(f"Error publishing message to {destination}: {str(e)}")
            
            print("Published data to Solace")
        except Exception as e:
            print(f"Error setting up publisher: {e}")
        finally:
            if direct_publish_service:
                direct_publish_service.terminate()


# Define grid boundaries (approximate for Ottawa)
LAT_MIN, LAT_MAX = 45.0, 46.0
LON_MIN, LON_MAX = -76.0, -75.0
GRID_SIZE = 0.1  # Approximately 11km grid cells

def get_grid_cell(lat, lon):
    lat_index = int((lat - LAT_MIN) / GRID_SIZE)
    lon_index = int((lon - LON_MIN) / GRID_SIZE)
    return f"{lat_index},{lon_index}"

def fetch_vehicle_positions():
    try:
        response = requests.get(VEHICLE_POSITIONS_URL, headers={'Ocp-Apim-Subscription-Key': API_KEY})
        response.raise_for_status()
        
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        return feed
    except requests.RequestException as e:
        print(f"Error fetching vehicle positions: {e}")
        return None

def process_vehicle_data(feed):
    if not feed:
        return {}
    
    grid_data = {}
    
    for entity in feed.entity:
        if entity.HasField('vehicle'):
            vehicle = entity.vehicle
            lat = vehicle.position.latitude
            lon = vehicle.position.longitude
            grid_cell = get_grid_cell(lat, lon)
            
            vehicle_data = {
                "id": vehicle.vehicle.id,
                "trip_id": vehicle.trip.trip_id,
                "route_id": vehicle.trip.route_id,
                "latitude": lat,
                "longitude": lon,
                "speed": vehicle.position.speed,
                "timestamp": vehicle.timestamp
            }
            
            if grid_cell not in grid_data:
                grid_data[grid_cell] = []
            grid_data[grid_cell].append(vehicle_data)
    
    return grid_data

@app.get("/api/vehicle-positions")
async def get_vehicle_positions():
    feed = fetch_vehicle_positions()
    grid_data = process_vehicle_data(feed)
    publish_to_broker(grid_data)
    return grid_data

if __name__ == "__main__":
    initialize_broker()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)