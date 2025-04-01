/**
 * Printer Connection Manager - Frontend JavaScript
 */

// DOM Elements
const statusElement = document.getElementById('connection-status');
const methodElement = document.getElementById('connection-method');
const addressElement = document.getElementById('connection-address');
const modelElement = document.getElementById('printer-model');
const deviceContainer = document.getElementById('device-container');
const deviceList = document.getElementById('device-list');

// Buttons
const scanSystemBtn = document.getElementById('scan-system');
const printTestBtn = document.getElementById('print-test');

// Input fields
const firstNameInput = document.getElementById('first-name');
const lastNameInput = document.getElementById('last-name');

// Global state
let printerConnected = false;

/**
 * Update connection status UI
 * @param {Object} data - Printer connection data
 */
function updateConnectionStatus(data) {
    statusElement.textContent = data.status;
    methodElement.textContent = data.method || 'None';
    addressElement.textContent = data.address || 'None';
    modelElement.textContent = data.model;
    
    // Update global connected state
    printerConnected = data.connected;
    
    statusElement.className = 'connection-status';
    if (data.connected) {
        statusElement.classList.add('connected');
        printTestBtn.disabled = false;
    } else if (data.status.includes('Searching') || data.status.includes('Trying')) {
        statusElement.classList.add('searching');
        printTestBtn.disabled = true;
    } else {
        statusElement.classList.add('disconnected');
        printTestBtn.disabled = true;
    }
}

/**
 * Fetch current printer status
 */
function fetchStatus() {
    fetch('/api/printer/status')
        .then(response => response.json())
        .then(data => {
            updateConnectionStatus(data);
        })
        .catch(error => {
            console.error('Error fetching status:', error);
            // Show error in UI
            statusElement.textContent = 'Error connecting to server';
            statusElement.className = 'connection-status disconnected';
        });
}

/**
 * Show list of found devices
 * @param {string} type - Device type (System)
 * @param {Array} devices - List of devices
 */
function showDeviceList(type, devices) {
    // Clear previous list
    deviceList.innerHTML = '';
    
    // Add each device to the list
    devices.forEach(device => {
        const item = document.createElement('div');
        item.className = 'device-item';
        item.textContent = `${device.name} (${device.address})`;
        item.addEventListener('click', function() {
            connectToDevice('system', device.address);
        });
        deviceList.appendChild(item);
    });
    
    // Show the container
    deviceContainer.style.display = 'block';
}

/**
 * Connect to a selected device
 * @param {string} method - Connection method
 * @param {string} address - Device address
 */
function connectToDevice(method, address) {
    fetch('/api/printer/connect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            address: address,
            method: method
        })
    })
    .then(response => response.json())
    .then(data => {
        updateConnectionStatus(data);
        deviceContainer.style.display = 'none';
    })
    .catch(error => {
        console.error('Error:', error);
        statusElement.textContent = 'Connection error';
        statusElement.className = 'connection-status disconnected';
    });
}

// Check for System printers
scanSystemBtn.addEventListener('click', function() {
    this.disabled = true;
    statusElement.textContent = 'Checking system printers...';
    statusElement.className = 'connection-status searching';
    printTestBtn.disabled = true;
    
    fetch('/api/printer/scan/system', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.devices && data.devices.length > 0) {
                showDeviceList('System', data.devices);
                statusElement.textContent = `Found ${data.devices.length} system printer(s)`;
            } else {
                alert('No system printers found');
                statusElement.textContent = 'No system printers found';
                statusElement.className = 'connection-status disconnected';
                printTestBtn.disabled = true;
            }
            this.disabled = false;
        })
        .catch(error => {
            console.error('Error:', error);
            this.disabled = false;
            statusElement.textContent = 'Scan error';
            statusElement.className = 'connection-status disconnected';
            printTestBtn.disabled = true;
        });
});

// Print test
printTestBtn.addEventListener('click', function() {
    const firstName = firstNameInput.value;
    const lastName = lastNameInput.value;
    
    if (!firstName || !lastName) {
        alert('Please enter both first and last name');
        return;
    }
    
    if (!printerConnected) {
        alert('Please connect to a printer first');
        return;
    }
    
    this.disabled = true;
    
    fetch('/print-name', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            attendee_firstname: firstName,
            attendee_lastname: lastName
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            alert('Print successful!');
        }
        this.disabled = false;
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error: ' + error);
        this.disabled = false;
    });
});

// Initial setup - disable print button until connected
printTestBtn.disabled = true;

// Initial status fetch
fetchStatus();

// Periodically update status
setInterval(fetchStatus, 2000);