import React, { useState, useEffect } from 'react';
import solace from 'solclientjs';
import OttawaMap from './Components/OttawaMap'; 

const SOLACE_HOST = process.env.REACT_APP_SOLACE_HOST;
const SOLACE_VPN = process.env.REACT_APP_SOLACE_VPN;
const SOLACE_USERNAME = process.env.REACT_APP_SOLACE_USERNAME;
const SOLACE_PASSWORD = process.env.REACT_APP_SOLACE_PASSWORD;

function App() {
  const [gridData, setGridData] = useState({});
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [buses, setBuses] = useState({});

  useEffect(() => {
    // Initialize Solace client
    const factoryProps = new solace.SolclientFactoryProperties();
    factoryProps.profile = solace.SolclientFactoryProfiles.version10;
    solace.SolclientFactory.init(factoryProps);

    // Create session
    const session = solace.SolclientFactory.createSession({
      url: SOLACE_HOST,
      vpnName: SOLACE_VPN,
      userName: SOLACE_USERNAME,
      password: SOLACE_PASSWORD,
    });

    // Define session event listeners
    session.on(solace.SessionEventCode.UP_NOTICE, function (sessionEvent) {
      setConnectionStatus('Connected');
      console.log('=== Successfully connected and ready to subscribe. ===');
      subscribe(session);
    });

    session.on(solace.SessionEventCode.CONNECT_FAILED_ERROR, function (sessionEvent) {
      setConnectionStatus('Connection failed');
      console.log('Connection failed to the message router: ' + sessionEvent.infoStr);
    });

    session.on(solace.SessionEventCode.DISCONNECTED, function (sessionEvent) {
      setConnectionStatus('Disconnected');
      console.log('Disconnected.');
      if (session !== null) {
        session.dispose();
      }
    });

    // Define message event listener
    session.on(solace.SessionEventCode.MESSAGE, function (message) {
      const topic = message.getDestination().getName();
      const gridCell = topic.split('/')[2];
      const vehicles = JSON.parse(message.getSdtContainer().getValue());
      setBuses(prevBuses => ({...prevBuses, [gridCell]: vehicles}));
    });

    // Connect the session
    try {
      session.connect();
    } catch (error) {
      setConnectionStatus('Connection failed');
      console.log(error.toString());
    }

    // Cleanup
    return () => {
      if (session && session.isConnected) {
        session.disconnect();
      }
    };
  }, []);

  function subscribe(session) {
    if (session !== null) {
      try {
        // Subscribe
        session.subscribe(
          solace.SolclientFactory.createTopicDestination("buses/grid/>"),
          true,
          "buses",
          10000
        );
      } catch (error) {
        console.log(error.toString());
      }
    }
  }

  return (
    <div className="App">
      <h1>OC Transpo Vehicle Positions</h1>
      <p>Connection status: {connectionStatus}</p>
      <OttawaMap buses={buses} />
    </div>
  );
}

export default App;