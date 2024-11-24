document.addEventListener('DOMContentLoaded', function () {
    const sections = document.querySelectorAll('.section');
    const footerItems = document.querySelectorAll('.footer-item');
    const userID = document.getElementById('userID').value;
    const tunnelID = document.getElementById('tunnelID').value;
    const tunnelName = document.getElementById('tunnelName').value;
    const length = document.getElementById('length').value;
    const geofence = document.getElementById('geofence').value;
    const geofence_radius = document.getElementById('geofence_r').value;
    let currentUserLocation = { lat: null, lon: null };  // Declare a global object to store location

    document.getElementById('title').innerHTML = tunnelName;
    document.getElementById('tunnel_length').innerHTML = length;

    console.log("Tunnel Name:", tunnelName);
    console.log("User ID:", userID);
    console.log("Tunnel ID:", tunnelID);
    console.log("GeoFence Radius: ", geofence_radius);

    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Show Operations section by default
    document.getElementById('operation').classList.add('active');

    footerItems.forEach(item => {
        item.addEventListener('click', function () {
            const target = this.getAttribute('data-section');

            sections.forEach(section => {
                section.classList.remove('active');
            });

            document.getElementById(target).classList.add('active');

            // Initialize the map if the map section is clicked
            if (target === 'mapSection') {
                initializeMap();
            }
        });
    });

    // Fetch and sync tunnel data on first load
    syncTunnelData();

    function syncTunnelData() {
        fetch('/operation/fetch-tunnel-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ tunnelID })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Tunnel data fetched:', data);
                    updateLightUI(data.status); // Update light status
                } else {
                    console.error('Failed to fetch tunnel data:', data.message);
                }
            })
            .catch(error => {
                console.error('Error fetching tunnel data:', error);
            });
    }

    // Light Toggle Logic (already implemented)
    const lightStatusText = document.getElementById('lightStatusText');
    const lightStatus = document.getElementById('lightStatus');
    const lightStatusCircle = document.getElementById('lightStatusCircle');
    const toggleLightBtn = document.getElementById('toggleLight');

    function updateLightUI(status) {
        lightStatus.textContent = status;
        lightStatusText.style.color = status === 'ON' ? '#00ff00' : '#ff0000';
        lightStatusCircle.classList.toggle('on', status === 'ON');
        lightStatusCircle.classList.toggle('off', status !== 'ON');
        toggleLightBtn.textContent = status === 'ON' ? 'Turn OFF Lights' : 'Turn ON Lights';
    }

    toggleLightBtn.addEventListener('click', function () {
        const currentStatus = lightStatus.textContent.trim(); // Get current status
        const action = currentStatus === 'OFF' ? 'ON' : 'OFF';

        // Update UI optimistically
        updateLightUI(action);

        // Send the manual operation request to the backend
        manualLightOperation(userID, tunnelID, action);
    });

    function manualLightOperation(userID, tunnelID, action) {
        fetch('/operation/manual-operation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ userID, tunnelID, action })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Operation successful:', data.message);
                } else {
                    console.error('Operation failed:', data.message);
                    // Revert UI if the operation failed
                    updateLightUI(action === 'ON' ? 'OFF' : 'ON');
                }
            })
            .catch(error => {
                console.error('Error during manual operation:', error);
                // Revert UI on error
                updateLightUI(action === 'ON' ? 'OFF' : 'ON');
            });
    }

    // SOS Form Submission

    // Ensure these elements exist and log their IDs for debugging
    document.getElementById("tunneli").value = tunnelID;
    document.getElementById("tunnelN").value = tunnelName;
    document.getElementById("locopilotID").value = userID;
    //document.getElementById("lastLocation").value = `Lat: ${currentUserLocation.lat}, Lon: ${currentUserLocation.lon}`;
    document.getElementById("requestTime").value = new Date().toLocaleString();;
    document.getElementById("status").value = "Pending";

    // Debug logs to confirm the values are correctly assigned
    console.log("Tunnel ID:", document.getElementById("tunneli").value);
    console.log("Tunnel Name:", document.getElementById("tunnelN").value);
    console.log("Locopilot ID:", document.getElementById("locopilotID").value);
    console.log("Last Location:", document.getElementById("lastLocation").value);
    console.log("Request Time:", document.getElementById("requestTime").value);
    console.log("Status:", document.getElementById("status").value);


    const sosForm = document.getElementById('sos-form');
    const formResponse = document.getElementById('form-response');

    sosForm.addEventListener('submit', function (event) {
        event.preventDefault(); // Prevent page reload
    
        // Gather form data
        const issue = document.getElementById('issue').value;
        const issueType = document.getElementById('issueType').value;
        const tunnelID = document.getElementById('tunneli').value;  // Updated ID
        const tunnelName = document.getElementById('tunnelN').value; // Updated ID
        const locopilotID = document.getElementById('locopilotID').value;
    
        // Capture locations as an array
        const lastLocationInputs = document.querySelectorAll('.lastLocation'); // Input fields with class `lastLocation`
        const lastLocation = Array.from(lastLocationInputs).map(input => input.value); // Convert NodeList to array and extract values
    
        const requestTime = document.getElementById('requestTime').value;
        const status = document.getElementById('status').value;
    
        // Payload for the backend
        const sosData = {
            issue,
            issueType,
            tunnelID,
            tunnelName,
            locopilotID,
            lastLocation, // Submit location array
            requestTime,
            status
        };
    
        // Send data to backend
        fetch('/sos/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(sosData)
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    formResponse.textContent = 'SOS Request Submitted Successfully!';
                    formResponse.style.color = 'green';
                } else {
                    formResponse.textContent = 'Failed to Submit SOS Request.';
                    formResponse.style.color = 'red';
                }
            })
            .catch(error => {
                console.error('Error submitting SOS request:', error);
                formResponse.textContent = 'Error Submitting SOS Request.';
                formResponse.style.color = 'red';
            });
    
        // Reset the form fields
        document.getElementById('issue').value = '';
        document.getElementById('issueType').value = '';
        document.querySelectorAll('.lastLocation').forEach(input => input.value = ''); // Clear all location inputs
    });
    

    // Scheduling Form Submission
    const scheduleForm = document.getElementById('schedule-form');
    const scheduleResponse = document.getElementById('schedule-response');

    scheduleForm.addEventListener('submit', function (event) {
        event.preventDefault();
        const time = document.getElementById('time').value;
        scheduleResponse.textContent = `Schedule set for: ${time}`;
        scheduleForm.reset();
    });

    // Initialize Map with Geofence and Routing
    // Initialize Map with Geofence and Routing
    function initializeMap() {
        const [geofenceLat, geofenceLon] = geofence.split(',').map(coord => parseFloat(coord));

        if (isNaN(geofenceLat) || isNaN(geofenceLon)) {
            alert('Invalid geofence coordinates!');
            return;
        }

        const map = L.map('map').setView([geofenceLat, geofenceLon], 14);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        const circle = L.circle([geofenceLat, geofenceLon], {
            color: 'red',
            fillColor: '#f03',
            fillOpacity: 0.5,
            radius: geofence_radius
        }).addTo(map);

        L.marker([geofenceLat, geofenceLon]).addTo(map)
            .bindPopup(tunnelName + " Geofence")
            .openPopup();

        let currentMarker = null; // To store the user's location marker
        let routeControl = null;  // To store the route control

        function updateUserLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function (position) {
                        const currentLat = position.coords.latitude;
                        const currentLon = position.coords.longitude;
                        const accuracy = position.coords.accuracy;

                        if (accuracy < 1000) {
                            const currentLocation = [currentLat, currentLon];
                            currentUserLocation.lat = currentLat;
                            currentUserLocation.lon = currentLon;
                            console.log("Location", currentLocation);
                            document.getElementById("lastLocation").value = `Lat: ${currentUserLocation.lat}, Lon: ${currentUserLocation.lon}`;
                            console.log("Location lat", currentUserLocation.lat);
                            console.log("Location lon", currentUserLocation.lon);

                            // Clear old marker
                            if (currentMarker) map.removeLayer(currentMarker);

                            // Add a new marker for the user's current location
                            currentMarker = L.marker(currentLocation).addTo(map)
                                .bindPopup(`Your Current Location (Accuracy: ${accuracy} meters)`)
                                .openPopup();

                            // Clear old route
                            if (routeControl) map.removeControl(routeControl);

                            // Draw a route from user's current location to the geofence center
                            routeControl = L.Routing.control({
                                waypoints: [
                                    L.latLng(currentLat, currentLon),
                                    L.latLng(geofenceLat, geofenceLon)
                                ],
                                routeWhileDragging: true
                            }).addTo(map);
                        } else {
                            console.warn(`Location accuracy is too low (${accuracy} meters).`);
                        }
                    },
                    function (error) {
                        console.error(`Error retrieving location: ${error.message}`);
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 5000,
                        maximumAge: 0
                    }
                );
            } else {
                alert("Geolocation is not supported by this browser.");
            }
        }

        // Call the function initially
        updateUserLocation();

        // Refresh user location every 2 seconds
        setInterval(updateUserLocation, 2000);
    }
});
