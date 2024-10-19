document.addEventListener('DOMContentLoaded', function () {
    const sections = document.querySelectorAll('.section');
    const footerItems = document.querySelectorAll('.footer-item');

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

    

    // Light Toggle Logic
    const lightStatusText = document.getElementById('lightStatusText');
    const lightStatus = document.getElementById('lightStatus');
    const lightStatusCircle = document.getElementById('lightStatusCircle');
    const toggleLightBtn = document.getElementById('toggleLight');

    toggleLightBtn.addEventListener('click', function () {
        if (lightStatus.textContent === 'OFF') {
            lightStatus.textContent = 'ON';
            lightStatusText.style.color = '#00ff00';
            lightStatusCircle.classList.remove('off');
            lightStatusCircle.classList.add('on');
            toggleLightBtn.textContent = 'Turn OFF Lights';
            toggleLightBtn.classList.remove('off');
            toggleLightBtn.classList.add('on');
        } else {
            lightStatus.textContent = 'OFF';
            lightStatusText.style.color = '#ff0000';
            lightStatusCircle.classList.remove('on');
            lightStatusCircle.classList.add('off');
            toggleLightBtn.textContent = 'Turn ON Lights';
            toggleLightBtn.classList.remove('on');
            toggleLightBtn.classList.add('off');
        }
    });

    // SOS Form Submission
    const sosForm = document.getElementById('sos-form');
    const formResponse = document.getElementById('form-response');

    sosForm.addEventListener('submit', function (event) {
        event.preventDefault();
        const issue = document.getElementById('issue').value;
        formResponse.textContent = `SOS Request Submitted: "${issue}"`;
        sosForm.reset();
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
    function initializeMap() {
        // Initialize the map and set its view to the geofence center
        // Initialize the map and set its view to the geofence center
        var map = L.map('map').setView([18.730914125151042, 73.66339737643803], 14);

        // Add tile layer to the map
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        // Define the geofence circle
        var circle = L.circle([18.730914125151042, 73.66339737643803], {
            color: 'red',
            fillColor: '#f03',
            fillOpacity: 0.5,
            radius: 50
        }).addTo(map);

        // Marker for the geofence center
        var marker = L.marker([18.730914125151042, 73.66339737643803]).addTo(map)
            .bindPopup("Geofence Center")
            .openPopup();

        // Fetch and display the current location
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function (position) {
                    var currentLat = position.coords.latitude;
                    var currentLon = position.coords.longitude;
                    var accuracy = position.coords.accuracy;  // Accuracy in meters

                    // Check if the accuracy is sufficient (e.g., below 100 meters)
                    if (accuracy < 10000) {
                        var currentLocation = [currentLat, currentLon];

                        // Add a marker for the user's current location
                        var currentMarker = L.marker(currentLocation).addTo(map)
                            .bindPopup("Your Current Location (Accuracy: " + accuracy + " meters)")
                            .openPopup();

                        // Route from the user's current location to the center of the geofence
                        L.Routing.control({
                            waypoints: [
                                L.latLng(currentLat, currentLon),
                                L.latLng(18.730914125151042, 73.66339737643803)
                            ],
                            routeWhileDragging: true
                        }).addTo(map);

                        // Draw a straight line between the user's location and the geofence center
                        var line = L.polyline([
                            [currentLat, currentLon],
                            [18.730914125151042, 73.66339737643803]
                        ], { color: 'blue' }).addTo(map);
                    } else {
                        alert("Location accuracy is too low (" + accuracy + " meters). Please try again or move to an open area.");
                    }
                },
                function (error) {
                    alert("Error retrieving location: " + error.message);
                },
                {
                    enableHighAccuracy: true,  // Request high-accuracy location
                    timeout: 5000,             // Timeout after 5 seconds
                    maximumAge: 0              // Do not use cached location
                }
            );
        } else {
            alert("Geolocation is not supported by this browser.");
        }
    }
});
