import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const OttawaMap = ({ buses }) => {
  return (
    <MapContainer center={[45.4215, -75.6972]} zoom={13} style={{ height: '100vh', width: '100%' }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      {Object.values(buses).flat().map((bus) => (
        <Marker key={bus.id} position={[bus.latitude, bus.longitude]}>
          <Popup>
            Bus ID: {bus.id}<br />
            Route: {bus.route_id}<br />
            Speed: {bus.speed} m/s
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};

export default OttawaMap;