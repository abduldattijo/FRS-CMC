// Facial Recognition System - Frontend JavaScript

const API_BASE = '/api/v1';

// Utility Functions
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;

    const alertClass = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-error' : 'alert-info';
    const alertHTML = `<div class="alert ${alertClass}">${message}</div>`;

    alertContainer.innerHTML = alertHTML;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertContainer.innerHTML = '';
    }, 5000);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatConfidence(confidence) {
    return (confidence * 100).toFixed(1) + '%';
}

// Dashboard Functions
async function loadDashboardStats() {
    try {
        // Load persons count
        const personsResponse = await fetch(`${API_BASE}/persons/`);
        const personsData = await personsResponse.json();
        document.getElementById('total-persons').textContent = personsData.total || 0;

        // Load detection stats
        const statsResponse = await fetch(`${API_BASE}/detections/stats`);
        const statsData = await statsResponse.json();
        document.getElementById('total-detections').textContent = statsData.total_detections || 0;
        document.getElementById('unknown-faces').textContent = statsData.unknown_persons || 0;
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

async function loadRecentPersons() {
    try {
        const response = await fetch(`${API_BASE}/persons/?limit=5`);
        const data = await response.json();

        const container = document.getElementById('recent-persons');

        if (data.persons.length === 0) {
            container.innerHTML = '<p>No persons registered yet.</p>';
            return;
        }

        let tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Employee ID</th>
                        <th>Department</th>
                        <th>Email</th>
                        <th>Registered</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.persons.forEach(person => {
            tableHTML += `
                <tr>
                    <td>${person.name}</td>
                    <td>${person.employee_id || '-'}</td>
                    <td>${person.department || '-'}</td>
                    <td>${person.email || '-'}</td>
                    <td>${formatDate(person.created_at)}</td>
                </tr>
            `;
        });

        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;
    } catch (error) {
        console.error('Error loading recent persons:', error);
        document.getElementById('recent-persons').innerHTML = '<p>Error loading persons.</p>';
    }
}

// Video Upload Functions
function setupVideoUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('video-file');
    const form = document.getElementById('video-upload-form');

    if (!uploadArea || !fileInput || !form) return;

    // Click to upload
    uploadArea.addEventListener('click', () => fileInput.click());

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            uploadArea.innerHTML = `<p>Selected: ${files[0].name}</p>`;
        }
    });

    // File selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadArea.innerHTML = `<p>Selected: ${e.target.files[0].name}</p>`;
        }
    });

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await processVideo();
    });
}

async function processVideo() {
    const fileInput = document.getElementById('video-file');
    const frameSkip = document.getElementById('frame-skip').value;
    const saveFrames = document.getElementById('save-frames').checked;
    const processBtn = document.getElementById('process-btn');
    const processingStatus = document.getElementById('processing-status');
    const resultsContainer = document.getElementById('results-container');

    if (!fileInput.files || fileInput.files.length === 0) {
        showAlert('Please select a video file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('video', fileInput.files[0]);
    formData.append('frame_skip', frameSkip);
    formData.append('save_frames', saveFrames);

    try {
        processBtn.disabled = true;
        processingStatus.style.display = 'block';
        resultsContainer.style.display = 'none';

        // Use enhanced endpoint for cross-video face tracking
        const response = await fetch(`${API_BASE}/enhanced-video/process`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Processing failed');
        }

        const data = await response.json();

        // Hide processing, show results
        processingStatus.style.display = 'none';
        resultsContainer.style.display = 'block';

        // Display results
        displayVideoResults(data);
        showAlert('Video processed successfully!', 'success');

        // Refresh dashboard stats
        loadDashboardStats();

    } catch (error) {
        console.error('Error processing video:', error);
        showAlert(`Error: ${error.message}`, 'error');
        processingStatus.style.display = 'none';
    } finally {
        processBtn.disabled = false;
    }
}

function displayVideoResults(data) {
    const resultsStats = document.getElementById('results-stats');
    const resultsDetections = document.getElementById('results-detections');

    // Handle both enhanced and basic response formats
    const totalDetections = data.total_detections || 0;
    const processedFrames = data.processed_frames || 0;
    const processingTime = data.processing_time_seconds || 0;

    // Enhanced format has breakdown object
    let registeredCount, trackedUnknowns, newUnknowns;
    if (data.breakdown) {
        registeredCount = data.breakdown.registered_persons || 0;
        trackedUnknowns = data.breakdown.tracked_unknowns || 0;
        newUnknowns = data.breakdown.new_unknowns || 0;
    } else {
        // Basic format
        registeredCount = data.known_detections || 0;
        trackedUnknowns = 0;
        newUnknowns = data.unknown_detections || 0;
    }

    // Display statistics with enhanced breakdown
    resultsStats.innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">${totalDetections}</div>
                <div class="stat-label">Total Detections</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">${registeredCount}</div>
                <div class="stat-label">Registered Persons</div>
            </div>
            <div class="stat-card info">
                <div class="stat-value">${trackedUnknowns}</div>
                <div class="stat-label">Previously Seen Unknowns</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-value">${newUnknowns}</div>
                <div class="stat-label">New Unknown Persons</div>
            </div>
        </div>
        <p>Processed ${processedFrames} frames in ${processingTime.toFixed(2)} seconds</p>
        ${data.message ? `<p class="success-message">${data.message}</p>` : ''}
    `;

    // Display summary message
    if (totalDetections > 0) {
        let detectionsHTML = '<h4>Cross-Video Tracking Results:</h4><ul>';

        if (registeredCount > 0) {
            detectionsHTML += `<li><strong>${registeredCount}</strong> registered person(s) detected</li>`;
        }
        if (trackedUnknowns > 0) {
            detectionsHTML += `<li><strong>${trackedUnknowns}</strong> unknown person(s) matched from previous videos</li>`;
        }
        if (newUnknowns > 0) {
            detectionsHTML += `<li><strong>${newUnknowns}</strong> new unknown person(s) saved for future tracking</li>`;
        }

        detectionsHTML += '</ul>';

        if (newUnknowns > 0 || trackedUnknowns > 0) {
            detectionsHTML += `
                <div class="info-box">
                    <p><strong>Cross-Video Tracking Active!</strong></p>
                    <p><strong>From Previous Videos:</strong> ${trackedUnknowns} face(s) matched to people seen in earlier videos.</p>
                    ${newUnknowns > 0 ? `<p><strong>New Unique Persons:</strong> ${data.new_unknowns_created} unique unknown person(s) detected in this video and saved for future matching.</p>` : ''}
                    ${data.duplicates_merged > 0 ? `<p><em>Note: ${data.duplicates_merged} duplicate detection(s) of the same person in this video were automatically merged.</em></p>` : ''}
                </div>
            `;
        }

        resultsDetections.innerHTML = detectionsHTML;
    } else {
        resultsDetections.innerHTML = '<p>No faces detected in the video.</p>';
    }
}

// Person Registration Functions
function setupImageUpload() {
    const uploadArea = document.getElementById('image-upload-area');
    const fileInput = document.getElementById('face-image');
    const preview = document.getElementById('image-preview');
    const previewImg = document.getElementById('preview-img');

    if (!uploadArea || !fileInput) return;

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            previewImage(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            previewImage(e.target.files[0]);
        }
    });

    function previewImage(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
}

function setupRegisterForm() {
    const form = document.getElementById('register-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await registerPerson();
    });

    form.addEventListener('reset', () => {
        document.getElementById('image-preview').style.display = 'none';
    });
}

async function registerPerson() {
    const formData = new FormData();
    formData.append('name', document.getElementById('name').value);
    formData.append('employee_id', document.getElementById('employee-id').value);
    formData.append('email', document.getElementById('email').value);
    formData.append('phone', document.getElementById('phone').value);
    formData.append('department', document.getElementById('department').value);
    formData.append('notes', document.getElementById('notes').value);

    const imageFile = document.getElementById('face-image').files[0];
    if (!imageFile) {
        showAlert('Please select a face image', 'error');
        return;
    }
    formData.append('image', imageFile);

    const registerBtn = document.getElementById('register-btn');

    try {
        registerBtn.disabled = true;
        registerBtn.textContent = 'Registering...';

        const response = await fetch(`${API_BASE}/persons/`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }

        const data = await response.json();
        showAlert(`Successfully registered ${data.name}!`, 'success');

        // Reset form
        document.getElementById('register-form').reset();
        document.getElementById('image-preview').style.display = 'none';

        // Reload persons list
        loadPersonsList();

    } catch (error) {
        console.error('Error registering person:', error);
        showAlert(`Error: ${error.message}`, 'error');
    } finally {
        registerBtn.disabled = false;
        registerBtn.textContent = 'Register Person';
    }
}

async function loadPersonsList() {
    try {
        const response = await fetch(`${API_BASE}/persons/`);
        const data = await response.json();

        const container = document.getElementById('persons-table');

        if (data.persons.length === 0) {
            container.innerHTML = '<p>No persons registered yet.</p>';
            return;
        }

        let tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Employee ID</th>
                        <th>Email</th>
                        <th>Department</th>
                        <th>Status</th>
                        <th>Registered</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.persons.forEach(person => {
            const statusBadge = person.is_active ?
                '<span class="badge badge-success">Active</span>' :
                '<span class="badge badge-danger">Inactive</span>';

            tableHTML += `
                <tr>
                    <td>${person.name}</td>
                    <td>${person.employee_id || '-'}</td>
                    <td>${person.email || '-'}</td>
                    <td>${person.department || '-'}</td>
                    <td>${statusBadge}</td>
                    <td>${formatDate(person.created_at)}</td>
                </tr>
            `;
        });

        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;
    } catch (error) {
        console.error('Error loading persons:', error);
        document.getElementById('persons-table').innerHTML = '<p>Error loading persons.</p>';
    }
}

// Detection Monitoring Functions
async function loadDetectionStats() {
    try {
        const response = await fetch(`${API_BASE}/detections/stats`);
        const data = await response.json();

        document.getElementById('stat-total').textContent = data.total_detections || 0;
        document.getElementById('stat-known').textContent = data.known_persons || 0;
        document.getElementById('stat-unknown').textContent = data.unknown_persons || 0;
    } catch (error) {
        console.error('Error loading detection stats:', error);
    }
}

async function loadDetections(params = {}) {
    try {
        const queryParams = new URLSearchParams(params);
        const response = await fetch(`${API_BASE}/detections/?${queryParams}`);
        const data = await response.json();

        const tableContainer = document.getElementById('detections-table');
        const gridContainer = document.getElementById('detections-grid');

        if (data.detections.length === 0) {
            tableContainer.innerHTML = '<p>No detections found.</p>';
            gridContainer.innerHTML = '<p>No detection images available.</p>';
            return;
        }

        // Table view
        let tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Person</th>
                        <th>Video</th>
                        <th>Timestamp</th>
                        <th>Confidence</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.detections.forEach(det => {
            const statusBadge = det.is_unknown ?
                '<span class="badge badge-warning">Unknown</span>' :
                '<span class="badge badge-success">Known</span>';

            const confidence = det.confidence ? formatConfidence(det.confidence) : '-';

            tableHTML += `
                <tr>
                    <td>${det.person_name}</td>
                    <td>${det.video_name}</td>
                    <td>${formatDate(det.timestamp)}</td>
                    <td>${confidence}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        });

        tableHTML += '</tbody></table>';
        tableContainer.innerHTML = tableHTML;

        // Grid view with images
        let gridHTML = '';
        let imagesAvailable = 0;

        data.detections.forEach(det => {
            if (det.detection_image_path) {
                imagesAvailable++;

                // Extract filename from path and properly encode for URL
                const pathParts = det.detection_image_path.split('/');
                const filename = pathParts[pathParts.length - 1];
                const folderName = pathParts[pathParts.length - 2];

                // URL encode each part to handle special characters
                const encodedFolder = encodeURIComponent(folderName);
                const encodedFile = encodeURIComponent(filename);
                const imageUrl = `/detections/${encodedFolder}/${encodedFile}`;

                // Get reference image if available
                let referenceImageHtml = '';
                if (det.reference_image_path) {
                    let refUrl = '';
                    if (det.reference_image_path.includes('known_faces')) {
                        // Registered person image
                        const refFilename = det.reference_image_path.split('/').pop();
                        refUrl = `/known_faces/${encodeURIComponent(refFilename)}`;
                    } else {
                        // Unknown person reference image
                        const refParts = det.reference_image_path.split('/');
                        const refFilename = refParts[refParts.length - 1];
                        const refFolder = refParts[refParts.length - 2];
                        refUrl = `/detections/${encodeURIComponent(refFolder)}/${encodeURIComponent(refFilename)}`;
                    }
                    referenceImageHtml = `
                        <div style="position:absolute; top:5px; right:5px; background:rgba(0,0,0,0.7); padding:3px; border-radius:4px;">
                            <img src="${refUrl}"
                                 style="width:50px; height:50px; object-fit:cover; border:2px solid #fff; border-radius:4px;"
                                 title="Matched against this reference"
                                 onerror="this.style.display='none';">
                        </div>
                    `;
                }

                const statusClass = det.is_unknown ? 'warning' : 'success';
                const confidence = det.confidence ? formatConfidence(det.confidence) : 'N/A';

                gridHTML += `
                    <div class="detection-item" style="position:relative;">
                        <img src="${imageUrl}"
                             alt="${det.person_name}"
                             onerror="this.style.display='none';"
                             onload="this.style.opacity='1';"
                             style="opacity:0; transition: opacity 0.3s;">
                        ${referenceImageHtml}
                        <div class="detection-info">
                            <div class="detection-name">${det.person_name}</div>
                            <div class="detection-confidence">Confidence: ${confidence}</div>
                            <div class="detection-time">${formatDate(det.timestamp)}</div>
                            <span class="badge badge-${statusClass}">${det.is_unknown ? 'Unknown' : 'Known'}</span>
                        </div>
                    </div>
                `;
            }
        });

        if (imagesAvailable === 0) {
            gridContainer.innerHTML = '<p>No detection images available. Enable "Save Frames" when processing videos to see images.</p>';
        } else {
            gridContainer.innerHTML = gridHTML;
        }

    } catch (error) {
        console.error('Error loading detections:', error);
        document.getElementById('detections-table').innerHTML = '<p>Error loading detections.</p>';
    }
}

async function loadFilterOptions() {
    try {
        // Load persons for filter
        const personsResponse = await fetch(`${API_BASE}/persons/`);
        const personsData = await personsResponse.json();

        const personSelect = document.getElementById('filter-person');
        personsData.persons.forEach(person => {
            const option = document.createElement('option');
            option.value = person.id;
            option.textContent = person.name;
            personSelect.appendChild(option);
        });

        // Load videos for filter
        const videosResponse = await fetch(`${API_BASE}/video/uploads`);
        const videosData = await videosResponse.json();

        const videoSelect = document.getElementById('filter-video');
        videosData.videos.forEach(video => {
            const option = document.createElement('option');
            option.value = video.filename;
            option.textContent = video.filename;
            videoSelect.appendChild(option);
        });

    } catch (error) {
        console.error('Error loading filter options:', error);
    }
}

function applyFilters() {
    const params = {};

    const personId = document.getElementById('filter-person').value;
    if (personId) params.person_id = personId;

    const videoName = document.getElementById('filter-video').value;
    if (videoName) params.video_name = videoName;

    const unknownOnly = document.getElementById('filter-unknown').checked;
    if (unknownOnly) params.unknown_only = true;

    loadDetections(params);
}
